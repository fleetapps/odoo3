from ast import literal_eval

from odoo import Command
from odoo.fields import Domain

from .generator import Generator


class RelationOne(Generator):
    """Pick a random existing record ID from the comodel for Many2one fields."""
    name = 'relation.one'
    allowed_fields_type = ['many2one']

    def __init__(self, domain: Domain | None = None, ref: str | None = None, **kwargs):
        super().__init__(**kwargs)
        if domain is None:
            domain = []

        if ref is not None:
            ref_domain = Domain([
                ('res_model', '=', self.field.comodel_name),
                ('ref', '=', ref),
            ])
            if self.session:
                ref_domain &= Domain('session_id', '=', self.session.id)

            ref_records_ids = self.env['populate.model.data']._search(ref_domain).select('res_id')
            domain = Domain('id', 'in', ref_records_ids)

        # Note (perf): This can be a large list of ids,
        # but it's better than doing a search per yield
        self.comodel_ids = self.env[self.field.comodel_name].search(domain).ids

    def _next(self, known_vals):
        if not self.comodel_ids:
            return False

        if self.should_generate_null():
            return False

        if self.distribution:
            idx = self.distribution.sample_discrete(0, len(self.comodel_ids) - 1)
            return self.comodel_ids[idx]

        return self.rng.choice(self.comodel_ids)

    @classmethod
    def get_kwargs(cls, attrs):
        kwargs = super().get_kwargs(attrs)

        if 'domain' in attrs:
            kwargs['domain'] = literal_eval(attrs['domain'])

        if 'ref' in attrs:
            kwargs['ref'] = attrs['ref']

        return kwargs


class RelationMany(RelationOne):
    """Set a fixed ``count`` of random comodel records for X2many fields."""
    name = 'relation.many'
    allowed_fields_type = ['one2many', 'many2many']

    def __init__(self, count, **kwargs):
        super().__init__(**kwargs)
        if self.unique:
            # It makes little sense to have a unique constraint on a X2many field
            raise ValueError(self.env._("Unique cannot be used with the '%s' generator.", self.name))

        # TODO: allow to have some form of variance in the count of the related records
        self.count = count

    def _next(self, known_vals):
        if not self.comodel_ids or not self.count > 0:
            return False

        if self.should_generate_null():
            return False

        # Don't crash if count > len, just cap it.
        sample_count = min(self.count, len(self.comodel_ids))

        if self.distribution:
            sampled_ids = []
            for _ in range(sample_count):
                idx = self.distribution.sample_discrete(0, len(self.comodel_ids) - 1)
                sampled_ids.append(self.comodel_ids[idx])
            return [Command.set(sampled_ids)]

        sampled_ids = self.rng.sample(
            self.comodel_ids,
            sample_count,
        )
        return [Command.set(sampled_ids)]

    @classmethod
    def get_kwargs(cls, attrs):
        kwargs = super().get_kwargs(attrs)

        if 'count' in attrs:
            kwargs['count'] = int(attrs['count'])

        return kwargs
