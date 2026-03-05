import logging
from collections.abc import Iterable

from odoo.api import Environment

_logger = logging.getLogger(__name__)


def drop_pending_update(env: Environment, fnames: Iterable[str]):
    """Drop pending updates on dirty ``fnames`` for all models"""
    fnames = set(fnames)
    for field, ids in env.transaction.field_dirty.items():
        if field.name in fnames:
            ids.clear()

    # TODO(perf): can use the model from the field
    for model in env.values():
        model.invalidate_model(model._fields.keys() & fnames, flush=False)


class VirtualField:
    """
    Represents a field that exists only during data generation and is not persisted to the database.

    Virtual fields serve as intermediate computation steps in the data population pipeline.

    Virtual fields are particularly useful when you need to compute intermediate values
    that multiple real fields depend on, avoiding redundant calculations or complex
    lambda expressions.

    Example:
       In a blueprint definition, you might use a virtual 'markup' field to compute
       the actual 'cost' and 'price' fields:

       ```json
       {
           'price': {'generator': 'scalar.float', 'start': 1, 'end': 10},
           'markup': {'virtual': true, 'eval': '0.3'},
           'cost': {'virtual': true, 'eval': 'price / (1 + markup)'},
           'stock_quantity': {'eval': 'int(cost * 2)'}
       }
       ```

       Here, 'markup' and 'cost' are computed but not saved; only 'stock_quantity' is persisted.
    """

    def __init__(self, model_name: str, field_name: str):
        self.model_name = model_name
        self.name = field_name
        self.type = 'virtual'
        self.required = False

    def __str__(self):
        return f"{self.model_name}.{self.name}"

    def __repr__(self):
        return f"VirtualField({self.model_name!r}, {self.name!r})"
