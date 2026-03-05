from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Sequence
from random import Random
from typing import TYPE_CHECKING, final

from odoo import _
from odoo.tools import find_circular_dependency, str2bool, topological_sort
from odoo.tools.safe_eval import const_eval

from ..utils.distributions import Distribution

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Mapping
    from typing import Any

    from odoo.api import Environment, ValuesType
    from odoo.fields import Field

    from ..models.session import Session
    from ..utils.orm import VirtualField

GENERATORS_REGISTRY = {}
MAX_UNIQ_VAL_ITER = 10
NO_VALUE = object()
DEFAULT_WEIGHT = 1


class Generator(ABC):
    """
    Defines the base class `Generator` used to manage and generate values based on field
    attributes specified in a populate job.

    Concrete subclasses are registered in a global registry for retrieval.

    They must define a `name` class attribute and are responsible for implementing
    the `_next` method for value generation. `__init__` can be overridden to specify custom
    initialization parameters. If attributes from the field definition need to be converted into
    `__init__` arguments, override the `get_kwargs` class method to handle the conversion.

    :ivar name: The unique name for the generator, used as its identifier in the registry
     and how it's referenced in blueprints.
    :ivar allowed_fields_type: A list of allowed field types for this generator,
     or `None` for no restriction.
    """
    name: str = None
    allowed_fields_type: list[str] | None = None

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        if not inspect.isabstract(cls):
            if cls.name is None:
                raise TypeError(_(
                    "Concrete Generator subclass '%(classname)s' must define a 'name' class attribute.",
                    classname=cls.__qualname__,
                ))

            GENERATORS_REGISTRY[cls.name] = cls

    def _validate_field_type(self, field: Field | VirtualField):
        if self.allowed_fields_type is not None and field.type not in self.allowed_fields_type:
            raise TypeError(_(
                "Incompatible field type '%(field_type)s'. Expected field type(s): %(allowed_types)s.",
                field_type=field.type,
                allowed_types=self.allowed_fields_type,
            ))

    def __init__(
        self,
        field: Field | VirtualField,
        env: Environment,
        rng: Random | None = None,
        session: Session | None = None,
        valid_fields: Collection[str] | None = None,
        # Passed attributes
        values: Sequence[Any] | Mapping[Any, float] | None = None,
        depends: list[str] | None = None,
        null_frac: float = 0.3,
        distribution: Distribution | Callable[[Random], Distribution] | None = None,
        unique: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._validate_field_type(field)

        self.field = field
        self.env = env

        if rng is None:
            rng = Random()

        self.rng = rng
        self.session = session

        if valid_fields is None:
            if self.field.type == 'virtual':
                raise ValueError(self.env._(
                    "Cannot infer valid fields for a virtual field. "
                    "The 'valid_fields' parameter must be explicitly provided.",
                ))

            valid_fields = self.env[self.field.model_name]._fields.keys()

        if values is not None:
            if isinstance(values, Sequence):
                # A sequence is provided, then they have equal weights
                values = dict(zip(values, [DEFAULT_WEIGHT] * len(values)))

            if len(values.keys()) != len(set(values.keys())):
                # Having multiple instances of the same value will bias sampling
                raise ValueError(self.env._("Cannot have repeated entries in `values`."))

            self.weighted_values = values
        else:
            self.weighted_values = {}

        if depends is None:
            depends = []

        if not all(dep in valid_fields for dep in depends):
            invalid_fields = [dep for dep in depends if dep not in valid_fields]
            raise ValueError(self.env._(
                "Invalid field dependencies: %(invalid_fields)s. "
                "These fields do not exist in the model's blueprint.",
                invalid_fields=invalid_fields,
            ))

        self.depends = depends

        if not (0 <= null_frac <= 1):
            raise ValueError(self.env._(
                "Null fraction must be between 0 and 1, got %(null_frac)s instead.",
                null_frac=null_frac,
            ))

        if self.field.required:
            null_frac = 0

        if self.has_weights:
            # Don't generate False entries if the user provided weights.
            # It will throw off the requested bias.
            null_frac = 0

        self.null_frac = null_frac

        if distribution and self.has_weights:
            raise ValueError(self.env._(
                "Cannot have both a distribution and weighted values. "
                "Please provide either 'distribution' or 'values' with weights, but not both.",
            ))

        if isinstance(distribution, Distribution):
            self.distribution = distribution
        elif callable(distribution):
            self.distribution = distribution(self.rng)
        else:
            self.distribution = None

        self.unique = unique

        if self.unique:
            if self.field.type == 'virtual':
                # Virtual fields are computed and not stored in the database.
                # Since we can't query existing values from the database,
                # we can only guarantee uniqueness within the current job run.
                # Therefore, values may be duplicated across different jobs and/or populate sessions.
                self._seen = set()
            else:
                model_name = self.field.model_name
                field_name = self.field.name
                present_values = (
                    self.env[model_name]
                    .search_fetch([], [field_name])
                    .mapped(field_name)
                )
                self._seen = set(present_values)
        else:
            self._seen = None

    @property
    def values(self) -> list[Any]:
        return list(self.weighted_values.keys())

    @values.setter
    def values(self, new_values: Iterable):
        self.weighted_values = dict(zip(new_values, [DEFAULT_WEIGHT] * len(new_values)))

    @property
    def weights(self) -> list[float]:
        return list(self.weighted_values.values())

    @property
    def has_weights(self) -> bool:
        return not all(weight == DEFAULT_WEIGHT for weight in self.weighted_values.values())

    def should_generate_null(self) -> bool:
        return bool(self.null_frac and self.rng.random() < self.null_frac)

    @final
    def __iter__(self):
        return self

    @final
    def __next__(self):
        return self.next()

    @final
    def next(self, known_vals: ValuesType | None = None) -> Any:
        if known_vals is None:
            known_vals = {}

        if not all(dep in known_vals for dep in self.depends):
            return NO_VALUE

        if self.unique:
            for _ in range(MAX_UNIQ_VAL_ITER):
                value = self._next(known_vals)
                if value in self._seen:
                    continue

                self._seen.add(value)
                return value

            raise RuntimeError(self.env._(
                "Couldn't find a unique value for field %(field)s.",
                field=self.field,
            ))

        return self._next(known_vals)

    @abstractmethod
    def _next(self, known_vals: ValuesType) -> Any:
        """Generate the next value for this field based on known dependent field values."""
        ...

    @final
    def send(self, values: ValuesType) -> Any:
        return self.next(values)

    @classmethod
    def get_kwargs(cls, attrs: dict[str, str]) -> dict[str, Any]:
        """Convert the fields' attributes of job instructions into kwargs consumable by generators."""
        kwargs = {}

        if 'values' in attrs:
            kwargs['values'] = const_eval(attrs['values'])

        if 'null_frac' in attrs:
            kwargs['null_frac'] = float(attrs['null_frac'])

        if 'distribution' in attrs:
            distribution_def = attrs['distribution']
            distribution = Distribution.from_definition(distribution_def, partial=True)
            kwargs['distribution'] = distribution

        if 'unique' in attrs:
            value = attrs['unique']
            kwargs['unique'] = str2bool(value)

        if 'virtual' in attrs:
            # The field is of the type 'virtual', there is no need for an arg.
            attrs.pop('virtual')

        return kwargs

    @staticmethod
    def get(name: str) -> type[Generator]:
        return GENERATORS_REGISTRY[name]


def get_fields_vals(generators: Mapping[str, Generator]) -> ValuesType:
    """Get the vals for a specific record that needs to be created/written."""
    vals = {}

    fields_depends = {
        field_name: generator.depends
        for field_name, generator in generators.items()
    }
    if cycle := find_circular_dependency(fields_depends):
        chain = ' -> '.join(str(n) for n in cycle)
        raise RuntimeError(_(
            "Circular dependency detected in fields' generator dependencies: %(chain)s.",
            chain=chain,
        ))

    for field_name in topological_sort(fields_depends):
        generator = generators[field_name]
        try:
            value = generator.send(vals)

            if value is NO_VALUE:
                missing_deps = [dep for dep in generator.depends if dep not in vals]
                raise RuntimeError(_(  # noqa: TRY301
                    "Could not generate a value because "
                    "required dependencies are missing: %(missing_deps)s. "
                    "Expected dependencies: %(expected_deps)s.",
                    missing_deps=missing_deps,
                    expected_deps=generator.depends,
                ))

        except Exception as exc:
            exc.add_note(_("Generator: '%(name)s'", name=generator.name))
            exc.add_note(_("Field: '%(field)s'", field=generator.field))
            raise

        vals[field_name] = value

    # Remove values from virtual fields.
    # Virtual fields may have the same name as real fields,
    # but we should not commit their values to the database.
    for field_name, generator in generators.items():
        if generator.field.type == 'virtual':
            vals.pop(field_name)

    return vals
