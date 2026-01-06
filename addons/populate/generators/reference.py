from typing import TYPE_CHECKING, cast

from odoo.fields import Domain

from .generator import Generator

if TYPE_CHECKING:
    from odoo import fields


class ReferenceOne(Generator):
    """Pick a random record ID for a Many2oneReference field."""
    name = 'reference.one'
    allowed_fields_type = ['many2one_reference']

    def __init__(self, field: 'fields.Many2oneReference', **kwargs):
        # Validate field's type before reading `model_field`
        self._validate_field_type(field)
        super().__init__(field=field, depends=[field.model_field], **kwargs)
        self.field = cast('fields.Many2oneReference', self.field)

    def _next(self, known_vals):
        if self.should_generate_null():
            return False

        comodel_name = known_vals[self.field.model_field]
        # Not ideal, but this is better than keeping all record IDs in memory
        # for every model in the registry, since we cannot predict in advance
        # which model will be referenced by the generated model_field value.
        comodel_ids = self.env[comodel_name].search([]).ids

        if not comodel_ids:
            return False

        if self.distribution:
            idx = self.distribution.sample_discrete(0, len(comodel_ids) - 1)
            return comodel_ids[idx]

        return self.rng.choice(comodel_ids)


class ReferenceRaw(Generator):
    """Generate ``'model_name,id'`` strings for Reference fields."""
    name = 'reference.raw'
    allowed_fields_type = ['reference']

    def __init__(
        self,
        res_model: str | None = None,
        res_id: str | None = None,
        ref: str | None = None,
        **kwargs,
    ):
        depends = []
        if res_model:
            depends.append(res_model)
            if res_id:
                depends.append(res_id)

        super().__init__(depends=depends, **kwargs)
        self.field = cast('fields.Reference', self.field)

        self.res_model = res_model
        self.res_id = res_id
        self.ref = ref
        self.model_names = self.field.get_values(self.env)

    def _next(self, known_vals):
        if self.should_generate_null():
            return False

        if len(self.depends) == 2:
            model_name = known_vals[self.depends[0]]
            record_id = known_vals[self.depends[1]]

            if model_name not in self.model_names:
                raise ValueError(self.env._(
                    "Model '%(model_name)s' is not in the allowed models "
                    "for reference field '%(field_name)s': %(model_names)s.",
                    model_name=model_name,
                    field_name=self.field.name,
                    model_names=self.model_names,
                ))

            if isinstance(record_id, str):
                record_id = int(record_id)

            return f"{model_name},{record_id}"

        if len(self.depends) == 1:
            # Infer it's the `model_name`
            model_name = known_vals[self.depends[0]]

            if model_name not in self.model_names:
                raise ValueError(self.env._(
                    "Model '%(model_name)s' is not in the allowed models "
                    "for reference field '%(field_name)s': %(model_names)s.",
                    model_name=model_name,
                    field_name=self.field.name,
                    model_names=self.model_names,
                ))

        else:
            # distribution is applied on the ids, not the models
            model_name = self.rng.choice(self.model_names)

        assert model_name

        domain = []

        if self.ref is not None:
            ref_domain = Domain([
                ('res_model', '=', model_name),
                ('ref', '=', self.ref),
            ])
            if self.session:
                ref_domain &= Domain('session_id', '=', self.session.id)

            ref_records_ids = self.env['populate.model.data']._search(ref_domain).select('res_id')
            domain = Domain('id', 'in', ref_records_ids)

        comodel_ids = self.env[model_name].search(domain).ids

        if not comodel_ids:
            return False

        if self.distribution:
            idx = self.distribution.sample_discrete(0, len(comodel_ids) - 1)
            record_id = comodel_ids[idx]
        else:
            record_id = self.rng.choice(comodel_ids)

        return f"{model_name},{record_id}"

    @classmethod
    def get_kwargs(cls, attrs):
        kwargs = super().get_kwargs(attrs)
        kwargs.update(**{k: v for k, v in attrs.items() if k in ('res_model', 'res_id', 'ref')})
        return kwargs
