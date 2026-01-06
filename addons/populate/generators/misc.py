from odoo import _
from odoo.tools.safe_eval import safe_eval
from odoo.tools.view_validation import get_expression_field_names

from .generator import Generator


class Cycle(Generator):
    """Deterministically cycle through a list of values in order."""
    name = 'misc.cycle'
    allowed_fields_type = ['integer', 'float', 'char', 'text', 'html', 'date', 'datetime', 'virtual']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.values:
            raise ValueError(self.env._("Values cannot be empty for the cycle generator."))

        if self.has_weights:
            raise ValueError(self.env._("Weights cannot be provided for the cycle generator."))

        # The cycle generator cycles through values deterministically in order.
        # To prevent unintended False/None values, null_frac is set to 0.
        # If False/None values are needed, they should be explicitly included in the values list.
        self.null_frac = 0
        self.index = 0

    def _next(self, known_vals):
        value = self.values[self.index]
        self.index = (self.index + 1) % len(self.values)
        return value


class Eval(Generator):
    """Evaluate a Python expression, optionally depending on other fields."""
    name = 'misc.eval'

    def __init__(self, expr: str, **kwargs):
        if expr.strip().startswith('lambda'):
            raise ValueError(_(
                "The eval generator takes an expression directly instead of a lambda. "
                "Use 'x + y' instead of 'lambda x, y: x + y'.",
            ))

        required_names = get_expression_field_names(expr)
        depends = list(required_names) if required_names else None

        super().__init__(depends=depends, **kwargs)

        if self.is_dynamic:
            # it's a raw expression that has dependencies,
            # wrap it into a lambda that takes the depends as args.
            args = ', '.join(self.depends)
            expr = f'lambda {args}: {expr}'

        evaluation = safe_eval(expr)

        if self.is_static and self.unique:
            raise ValueError(self.env._("This Eval returns the same value, so it cannot be unique."))

        # static -> evaluation is a value
        # dynamic -> evaluation is a lambda function
        self.evaluation = evaluation

    def _next(self, known_vals):
        if self.is_static:
            return self.evaluation

        kwargs = {dep: known_vals[dep] for dep in self.depends}
        return self.evaluation(**kwargs)

    @classmethod
    def get_kwargs(cls, attrs):
        kwargs = super().get_kwargs(attrs)

        if 'eval' in attrs:
            kwargs['expr'] = attrs['eval']

        return kwargs

    @property
    def is_static(self):
        """Invocations of the generator always yield the same value."""
        return not self.is_dynamic

    @property
    def is_dynamic(self):
        """Invocations of the generator can yield different values."""
        return bool(self.depends)
