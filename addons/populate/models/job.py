import logging
import time
from collections.abc import Mapping
from contextlib import contextmanager
from random import Random
from typing import Self

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import str2bool

from ..generators import Generator, get_fields_vals
from ..utils import seed
from ..utils.orm import VirtualField, drop_pending_update

MAX_RECORD_COMMIT_SIZE = 10000

_logger = logging.getLogger(__name__)


class Job(models.Model):
    """
    Single unit of work that creates or updates records for one model.

    A job is produced by instantiating a ``populate.blueprint``
    associated with a ``populate.session``. Large jobs are automatically
    split into smaller sub-jobs to allow for more frequent commits,
    preventing excessive memory usage, and enable parallel execution across multiple workers.
    """
    _name = 'populate.job'
    _description = 'Data Population Job'
    _order = 'session_id.id, id ASC'  # the order of `id ASC` is in the order of resolved ref dependencies

    seed = fields.Integer()
    parent_id = fields.Many2one('populate.job', index=True)
    child_ids = fields.One2many('populate.job', inverse_name='parent_id')
    parent_path = fields.Char(compute='_compute_parent_path')
    blueprint_id = fields.Many2one(
        'populate.blueprint',
        related='session_id.blueprint_id',
        store=True,  # avoid joining `populate.session` when searching on `populate.model.data`
        required=True,
        index=True,
        precompute=True,
    )
    session_id = fields.Many2one('populate.session', required=True, index=True)
    is_done = fields.Boolean()

    ref = fields.Char(help="""Reference the batch of records used by the job.
    If the job type is 'create' -> Annotates the records for referencing.
    If the job type is 'write' -> Refers to records with said reference.
    """)
    model_name = fields.Char(required=True)
    record_count = fields.Integer(default=1)
    type = fields.Selection([
        ('create', "Create"),
        ('write', "Write"),
    ], default='create', required=True)
    parallel = fields.Boolean(help="Can the job be executed in parallel?", default=True)
    context = fields.Json()
    instructions = fields.Json()

    _record_count_is_positive = models.Constraint('CHECK (record_count > 0)')
    # partial unique constraint, subjobs copy the info from parents,
    # and you can have multiple write jobs refer the same created records' ref.
    _unique_ref_per_session = models.UniqueIndex(
        "(ref, session_id) WHERE parent_id IS NULL AND type = 'create'",
        "A job with this reference already exists in this session. "
        "References must be unique for create-type jobs within a session.",
    )
    _records_idx = models.Index('(model_name, ref, session_id, blueprint_id)')

    @api.constrains('session_id', 'child_ids', 'parent_id')
    def _check_same_session(self):
        for session, jobs in self.grouped('session_id').items():
            if jobs.parent_id and jobs.parent_id.session_id != session:
                raise ValidationError(self.env._("Jobs in the same hierarchy should share the same session."))

    @api.constrains('child_ids', 'parent_id')
    def _check_parent_hierarchy(self):
        if self._has_cycle():
            raise ValidationError(self.env._("Job hierarchy cannot be recursive."))

    @api.constrains('child_ids', 'parent_id')
    def _check_single_level_hierarchy(self):
        for job in self:
            if job.parent_id and job.child_ids:
                raise ValidationError(self.env._(
                    "Children jobs cannot have child jobs themselves. Only one level of hierarchy is allowed.",
                ))

    @property
    def is_executable(self) -> bool:
        """Whether this job performs actual work."""
        self.ensure_one()
        return self.parent_id or not self.child_ids

    @property
    def pending_subjobs(self) -> Self:
        self.ensure_one()
        return self.child_ids.filtered(lambda job: not job.is_done)

    @property
    def progress(self) -> float:
        """Get the progress of the job as value between [0, 1]"""
        self.ensure_one()
        if self.parent_id:
            done = sum(sibling_job.record_count for sibling_job in self.parent_id.child_ids if sibling_job.is_done)
            total = self.parent_id.record_count
        else:
            if self.is_executable:
                done = self.record_count if self.is_done else 0
            else:
                done = sum(subjob.record_count for subjob in self.child_ids if subjob.is_done)
            total = self.record_count

        return done / total

    @api.depends('parent_id')
    def _compute_parent_path(self):
        for job in self:
            job.parent_path = (
                f'{job.parent_id.id}/{job.id}'
                if job.parent_id
                else f'{job.id}'
            )

    @api.private
    @api.model_create_multi
    def create(self, vals_list):
        jobs = super().create(vals_list)
        jobs += jobs._create_subjobs()

        if jobs:
            seeds = jobs.mapped('seed')
            assert len(seeds) == len(set(seeds)), "All job seeds must be unique"

        return jobs

    def _create_subjobs(self) -> Self:
        """
        Given a job, create the subjobs based on the session, if necessary.
        A subjob, by design, is the same as its parent, it just has a smaller `record_count`,
        based on the sessions `worker_count` and the cap of records that can be committed in one go.
        Their main goal is to allow horizontal scaling and prevent memory issues.
        """
        assert all(job.session_id for job in self), \
            "Cannot create sub-jobs without an attached session"

        jobs = self.filtered(lambda job: (
            not job.child_ids      # Already has subjobs, do not recreate them.
            and not job.parent_id  # Subjobs cannot have subjobs of their own
        ))

        subjob_vals = []
        for job in jobs:
            worker_count = job.session_id.worker_count
            total_records = job.record_count

            if total_records <= MAX_RECORD_COMMIT_SIZE:
                continue

            records_per_worker = total_records // worker_count
            remaining_records = total_records % worker_count

            for worker_index in range(worker_count):
                base_seed = job.seed
                # Spread remaining records over all workers
                worker_records = records_per_worker + (1 if worker_index < remaining_records else 0)

                while worker_records > 0:
                    batch_size = min(worker_records, MAX_RECORD_COMMIT_SIZE)
                    vals = job.copy_data(default={
                        'parent_id': job.id,
                        'record_count': batch_size,
                    })[0]
                    # Assign a unique seed to each subjob to prevent identical random sequences
                    # when subjobs run in parallel. The seed is deterministically derived from:
                    # - base_seed: updated after each derivation to differentiate subjobs
                    #   that may execute on the same worker sequentially
                    # - worker_index: ensures subjobs on different workers have different seeds
                    # Without unique seeds, parallel subjobs would generate identical values,
                    # defeating the purpose of probability distributions and weighted selections,
                    # or violate unique constraints.
                    vals['seed'] = base_seed = seed.derive_from(base_seed, worker_index)
                    subjob_vals.append(vals)
                    worker_records -= batch_size

        if subjob_vals:
            return self.env['populate.job'].create(subjob_vals)

        return self.env['populate.job']

    @api.private
    def execute(self, generators: Mapping[str, Generator] | None = None):
        """
        Execute a job.
        If the job has children, execute those, and considers itself done when all children are done
        If the job is a singleton (no parent and no children) or it's a subjob, execute the job itself.

        Side effect: commits transaction when successfully executed.
        """
        self.ensure_one()
        assert not self.is_done, "Cannot execute a job that is already done"
        assert self.seed, "The Job should have a `seed` set from the Session"

        with self.execution_scope():
            self._execute(generators)

    def _execute(self, generators: Mapping[str, Generator] | None = None):
        self.ensure_one()
        # Shouldn't raise, a locked job -> in progress
        self.lock_for_update()

        # A generator's scope is applicable per whole job, sub-job included.
        if generators is None:
            generators = self._create_generators()

        if self.is_executable:
            match self.type:
                case 'create':
                    self._execute_create(generators)
                case 'write':
                    self._execute_write(generators)
        else:
            for subjob in self.pending_subjobs:
                subjob.execute(generators)

    def _execute_create(self, generators: Mapping[str, Generator]):
        self.ensure_one()
        assert self.type == 'create'

        model = self.env[self.model_name]
        records_vals = []

        for _ in range(self.record_count):
            vals = get_fields_vals(generators)
            records_vals.append(vals)

        if context := self.context:
            model = model.with_context(**context)

        new_records = model.create(records_vals)

        self.env['populate.model.data'].create([{
            'res_id': record_id,
            'job_id': self.id,
        } for record_id in new_records.ids])

    def _execute_write(self, generators: Mapping[str, Generator]):
        self.ensure_one()
        assert self.type == 'write'

        if self.ref:
            populated_records_ids = self.env['populate.model.data']._search([
                ('ref', '=', self.ref),
                ('blueprint_id', '=', self.blueprint_id.id),
                ('session_id', '=', self.session_id.id),
                ('res_model', '=', self.model_name),
            ]).select('res_id')
            domain = [('id', 'in', populated_records_ids)]
        else:
            domain = []

        slice_kwargs = {}
        if self.parent_id:
            preceding_siblings = self.parent_id.child_ids.filtered(lambda job: job.id < self.id)
            slice_kwargs['offset'] = sum(job.record_count for job in preceding_siblings)
            slice_kwargs['limit'] = self.record_count

        records = self.env[self.model_name].search(domain, **slice_kwargs)

        for record in records:
            vals = get_fields_vals(generators)
            record.write(vals)

    def _create_generators(self) -> Mapping[str, Generator]:
        self.ensure_one()
        generators = {}
        model = self.env[self.model_name]
        valid_fields = self.instructions.keys()
        rng = Random(self.seed)
        for field_name, attrs in self.instructions.items():
            if str2bool(attrs.get('virtual', False)):
                field = VirtualField(self.model_name, field_name)
            else:
                field = model._fields[field_name]

            # If the generator is missing,
            # assume it's `eval` -> the generator is `misc.eval`.
            generator_name = attrs.get('generator', 'misc.eval')
            generator = Generator.get(generator_name)
            kwargs = {
                'field': field,
                'env': self.env,
                'rng': rng,
                'session': self.session_id,
                'valid_fields': valid_fields,
                **generator.get_kwargs(attrs),
            }
            try:
                generators[field_name] = generator(**kwargs)
            except Exception as exc:
                exc.add_note(self.env._("Generator: '%s'", generator_name))
                exc.add_note(self.env._("Field: '%s'", field))
                if self.ref:
                    exc.add_note(self.env._("Ref: '%s'", self.ref))
                raise

        return generators

    def _log_start(self):
        self.ensure_one()
        progress_info = f'- Session: {self.session_id.progress * 100:.0f}%'
        ref_info = f' [{self.ref}]' if self.ref else ''

        if self.is_executable:
            action = 'Creating' if self.type == 'create' else 'Writing on'

            if self.parent_id:
                progress_info = f'- Job: {self.progress * 100:.0f}% ' + progress_info

            _logger.info(
                "Job %(id)s: %(action)s %(count)d %(model)s%(ref)s %(progress)s",
                {
                    'id': self.parent_path,
                    'action': action,
                    'count': self.record_count,
                    'model': self.model_name,
                    'ref': ref_info,
                    'progress': progress_info,
                },
            )
        else:
            is_parallel = self.parallel and self.session_id.is_parallel
            parallel_info = ' (parallel)' if is_parallel else ''
            _logger.info(
                "Job %(id)s: Planning %(job_count)d subjobs for %(model)s%(ref)s (%(record_count)d records) %(progress)s%(parallel)s",
                {
                    'id': self.id,
                    'job_count': len(self.child_ids),
                    'model': self.model_name,
                    'ref': ref_info,
                    'record_count': self.record_count,
                    'progress': progress_info,
                    'parallel': parallel_info,
                },
            )

    def _log_end(self, elapsed_time):
        self.ensure_one()
        progress_info = f'- Session: {self.session_id.progress * 100:.0f}%'

        if self.parent_id:
            progress_info = f'- Job: {self.progress * 100:.0f}% ' + progress_info

        _logger.info(
            "Job %(id)s: Completed in %(time).2fs %(progress)s",
            {
                'id': self.parent_path,
                'time': elapsed_time,
                'progress': progress_info,
            },
        )

    @contextmanager
    def execution_scope(self):
        self.ensure_one()
        start_time = time.time()
        self._log_start()

        yield self

        if self.is_executable and self.parallel and self.session_id.is_parallel:
            # Discard pending updates to audit log fields (write_uid, write_date) to prevent some
            # serialization errors during data population, where such metadata is not essential.
            drop_pending_update(self.env, ['write_uid', 'write_date'])

        self.is_done = True
        self.env.cr.commit()
        self._log_end(elapsed_time=time.time() - start_time)
