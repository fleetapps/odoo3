from __future__ import annotations

import math
import random
import string
from collections import defaultdict
from typing import TYPE_CHECKING

from odoo import api, fields, models
from odoo.exceptions import ValidationError

if TYPE_CHECKING:
    from .session import Session

from ..utils import seed, xml

DEFINITION_PREFETCH_GROUP = 'Definitions'


class Blueprint(models.Model):
    """
    Declarative definition of what synthetic data to create.

    A blueprint holds an XML or JSON definition describing which models to
    populate, how many records to create, and which generators to use for
    each field.  It supports simple inheritance via ``parent_id``
    (XPath specs applied to the parent's XML).

    Blueprints are instantiated into ``populate.job`` records
    within a ``populate.session`` at execution time.
    """
    _name = 'populate.blueprint'
    _description = 'Data Population Blueprint'

    name = fields.Char("Blueprint name", required=True)
    parent_id = fields.Many2one(
        comodel_name='populate.blueprint',
        string='Inherited Blueprint',
        ondelete='set null',
        index=True,
        help="Blueprint to inherit from. Use XPath expressions in definition_xml to modify the parent.",
    )
    definition_xml = fields.Char("Raw XML Definition", prefetch=DEFINITION_PREFETCH_GROUP)
    definition_json = fields.Json("Raw JSON Definition", prefetch=DEFINITION_PREFETCH_GROUP)
    definition = fields.Json(
        string="JSON Definition",
        compute='_compute_definition',
        prefetch=DEFINITION_PREFETCH_GROUP,
        readonly=True,
    )

    _has_definition = models.Constraint(
        'CHECK(definition_xml IS NOT NULL OR definition_json IS NOT NULL)',
        "Either XML or JSON definition must be provided",
    )

    @api.constrains('parent_id')
    def _check_inheritance_recursion(self):
        if self._has_cycle('parent_id'):
            raise ValidationError(self.env._("You cannot create recursive inherited blueprints."))

    @api.depends('definition_xml', 'definition_json')
    def _compute_definition(self):
        """
        Compute the blueprint's definition in JSON.
        If both raw definitions are specified, the XML one takes precedence.
        If parent_id is set, apply inheritance specs first.
        """
        for blueprint in self:
            resolved_definition = blueprint.get_resolved_definition()
            if resolved_definition:
                blueprint.definition = xml.parse(resolved_definition)
            else:
                blueprint.definition = blueprint.definition_json

    @api.private
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if definition_xml := vals.get('definition_xml'):
                vals['definition_xml'] = xml.ensure_root(definition_xml)

        return super().create(vals_list)

    @api.private
    def write(self, vals):
        if definition_xml := vals.get('definition_xml'):
            vals['definition_xml'] = xml.ensure_root(definition_xml)

        return super().write(vals)

    @api.private
    def instantiate(self, session: Session):
        """Create new jobs to be run and link them to a Session."""
        self.ensure_one()
        if session.blueprint_id != self:
            raise ValueError(self.env._(
                "Blueprint '%(blueprint_name)s' can only be instantiated for a session that is associated with this blueprint. "
                "The provided session is associated with blueprint '%(actual_name)s'.",
                blueprint_name=self.name,
                actual_name=session.blueprint_id.name if session.blueprint_id else 'None',
            ))

        if session.job_ids:
            return  # Session already has jobs -> do nothing

        scaling_factor = session.scaling_factor or 1
        vals_list = []
        write_target_counts = defaultdict(lambda: defaultdict(int))  # {ref | None: {model_name: count}}
        for index, model in enumerate(self.get_explicit_definition()):
            model_name = model['name']
            ref = model.get('ref')
            vals = {
                'model_name': model_name,
                'instructions': model['fields'],
                'session_id': session.id,
                'seed': seed.derive_from(session.seed, index),
            }
            if 'count' in model:
                factor = scaling_factor if model.get('scale', True) else 1
                vals['record_count'] = math.floor(model['count'] * factor)

            vals.update(**{k: v for k, v in model.items() if k in ('type', 'ref', 'parallel', 'context')})

            defaults = self.env['populate.job'].default_get(['type', 'record_count'])
            is_create = vals.get('type', defaults['type']) == 'create'

            if is_create:
                write_target_counts[ref][model_name] += vals.get('record_count', defaults['record_count'])
            else:
                # Compute write job record_count:
                # - with 'ref': count from the matching 'create' job
                # - without 'ref': existing DB records + all preceding 'create' jobs for this model
                if ref:
                    assert ref in write_target_counts, "Create 'refs' should be present before its' writes"
                    vals['record_count'] = write_target_counts[ref][model_name]
                else:
                    existing = self.env[model_name].search_count([])
                    from_creates = write_target_counts[None][model_name]
                    total = existing + from_creates
                    if total > 0:
                        vals['record_count'] = total

            vals_list.append(vals)

        self.env['populate.job'].create(vals_list)

    @api.private
    def get_resolved_definition(self):
        """Get the resolved XML definition of the blueprint, applying inheritance if needed."""
        self.ensure_one()

        if not self.definition_xml:
            return None

        if not self.parent_id:
            return self.definition_xml

        parent_definition_xml = self.parent_id.get_resolved_definition()
        if not parent_definition_xml:
            raise ValueError(self.env._(
                "The parent blueprint '%(parent)s' does not have an XML definition, but is set as parent_id of '%(child)s'.",
                parent=self.parent_id.name,
                child=self.name,
            ))

        try:
            return xml.apply_inheritance(parent_definition_xml, self.definition_xml)
        except ValueError as e:
            raise ValueError(self.env._(
                "Error applying blueprint inheritance from %(parent)s' to %(child)s: %(error)s",
                parent=self.parent_id.name,
                child=self.name,
                error=e,
            ))

    @api.private
    def get_explicit_definition(self):
        """Transform the definition into a canonical form by applying a series of transformation steps."""

        def normalize_x2many(definition):
            """Normalize x2many definition by creating the referenced comodel before."""
            result = []
            for model in definition:
                model_name = model['name']
                for field_name, field_info in model['fields'].items():
                    if field_info.get('virtual', False):
                        continue

                    field = self.env[model_name]._fields[field_name]
                    if field.type in ('one2many', 'many2many') and (subfields := field_info.get('fields', {})):
                        ref = model.get('ref') or ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
                        comodel = {
                            'name': field.comodel_name,
                            'type': 'create',
                            'count': model['count'] * field_info['count'],
                            'ref': ref,
                            'fields': subfields,
                        }
                        new_model = {**model, 'ref': ref}
                        new_model['fields'][field_name]['fields'] = {}  # remove the subfields on the initial model
                        result += [comodel, new_model]
                        break
                else:
                    result.append(model)

            return result

        def reference_precedence(definition):
            """Allow out-of-order usage of `ref` (`id` doesn't need to precede the `ref`)"""
            ref_seen = set()
            pending = []
            result = []

            for model in definition:
                ref = model.get('ref')
                is_create = not model.get('type') or model.get('type') == 'create'

                # Can process now?
                if not ref or is_create or ref in ref_seen:
                    if ref and is_create:
                        ref_seen.add(ref)
                    result.append(model)
                else:
                    # Defer until ref is defined
                    pending.append(model)

            if pending and not result:
                pending_refs = [m.get('ref', '?') for m in pending]
                raise RuntimeError(self.env._(
                    "Unresolvable model references in blueprint '%(blueprint)s': "
                    "the following refs are used before being defined and no model defines them: %(refs)s.",
                    blueprint=self.name,
                    refs=pending_refs,
                ))

            return result + pending

        resolvers = [
            normalize_x2many,
            reference_precedence,
        ]
        definition = self.definition

        for resolver in resolvers:
            MAX_PASSES = 1_000
            passes = 0
            prev_definition, new_definition = None, definition
            while prev_definition != new_definition and passes < MAX_PASSES:
                prev_definition, new_definition = new_definition, resolver(new_definition)
                passes += 1

            if passes == MAX_PASSES:
                raise RecursionError(self.env._(
                    "Resolver %(resolver)s couldn't process %(definition)s in %(max_passes)s passes.",
                    resolver=resolver.__name__,
                    definition=self.definition,
                    max_passes=MAX_PASSES,
                ))

            definition = new_definition

        return definition

    def _register_hook(self):
        """Trigger loading of populate data files after all modules are loaded."""
        super()._register_hook()
        # Local import to avoid import failure due to partially initialized module
        from .. import _register_hook  # noqa: PLC0415
        # Evaluate if we need to install populate data after all modules were loaded.
        _register_hook(self.env)
