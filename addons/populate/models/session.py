from __future__ import annotations

import logging
import os
import secrets
import signal
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from typing import TYPE_CHECKING

import psycopg2
from psycopg2.errors import (
    CheckViolation,
    ExclusionViolation,
    NotNullViolation,
    UniqueViolation,
)

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import ConcurrencyError, LockError, UserError
from odoo.http.retrying import retrying
from odoo.modules.registry import Registry
from odoo.tools import str2bool

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from .job import Job

PG_EXCEPTIONS_TO_RETRY = (
    CheckViolation,
    ExclusionViolation,
    NotNullViolation,
    UniqueViolation,
)

_logger = logging.getLogger(__name__)


def has_platform_enabled_multiprocessing() -> bool:
    """Checks if the platform has allowed multiprocessing for the `populate` feature."""
    # opt-in by default, easier user onboarding.
    return str2bool(os.getenv('ODOO_POPULATE_MULTIPROCESS_ENABLE', 'True'))


class Session(models.Model):
    """
    Single execution run of a blueprint.

    A session owns the full set of ``populate.job`` records produced
    from its blueprint and tracks their completion state.
    Interrupted sessions can be resumed — only pending jobs are re-executed.
    """
    _name = 'populate.session'
    _description = 'Data Population Session'

    seed = fields.Integer("Seed", default=lambda _: secrets.randbits(31) - 1)
    scaling_factor = fields.Float("Scaling Factor")
    worker_count = fields.Integer("Number of parallel workers that will run jobs at the same time", default=1)
    blueprint_id = fields.Many2one('populate.blueprint', required=True)
    job_ids = fields.One2many('populate.job', inverse_name='session_id', domain=[('parent_id', '=', False)])

    @property
    def is_done(self) -> bool:
        self.ensure_one()
        return self.job_ids and all(self.job_ids.mapped('is_done'))

    @property
    def is_parallel(self) -> bool:
        self.ensure_one()
        return self.worker_count > 1

    @property
    def pending_jobs(self):
        self.ensure_one()
        return self.job_ids.filtered(lambda job: not job.is_done)

    @property
    def progress(self) -> float:
        """Get the progress of the session as value between [0, 1]"""
        self.ensure_one()
        return sum(job.progress for job in self.job_ids) / len(self.job_ids)

    @api.private
    @api.model_create_multi
    def create(self, vals_list):
        sessions = super().create(vals_list)
        assert not sessions.job_ids

        for session in sessions:
            session.blueprint_id.instantiate(session)

        return sessions

    @api.private
    def start(self):
        # We do not allow starting multiple sessions at once
        self.ensure_one()
        if self.is_done:
            raise UserError(self.env._(
                "The session %(session_id)s is already done. Create a new session.",
                session_id=self.id,
            ))

        try:
            # Prevent concurrent execution of the same session
            self.lock_for_update()

            assert self.job_ids, "A created session should have jobs instantiated"

            with JobExecutor.from_session(self) as executor:
                executor.execute(self.pending_jobs)

        except LockError as exc:
            raise UserError(self.env._("Session %(session_id)s is already running.", session_id=self.id)) from exc


class JobExecutor(ABC):
    """
    Abstract base class for job execution strategies.

    Selects the appropriate concrete executor based on the session configuration:
    use ``from_session`` as a context manager to get a ready-to-use executor.
    """

    @staticmethod
    @contextmanager
    def from_session(session: Session) -> AbstractContextManager[JobExecutor]:
        if session.is_parallel:
            if not has_platform_enabled_multiprocessing():
                raise RuntimeError(session.env._(
                    "The multiprocessing feature of the populate module has been disabled at the platform level.",
                ))

            Executor = ParallelExecutor
        else:
            Executor = SequentialExecutor

        with Executor.from_session(session) as executor:
            yield executor

    @abstractmethod
    def execute(self, jobs: Job):
        ...


class SequentialExecutor(JobExecutor):
    """
    Executes jobs one at a time in the current process.

    Jobs are run sequentially in the order they are provided.
    """

    @staticmethod
    @contextmanager
    def from_session(session: Session) -> AbstractContextManager[SequentialExecutor]:
        yield SequentialExecutor()

    def execute(self, jobs: Job):
        for job in jobs:
            job.execute()


class ParallelExecutor(JobExecutor):
    """
    Executes jobs using a pool of worker sub-processes via ``ProcessPoolExecutor``.

    Parallel execution is only applied to jobs that have child subjobs *and* have
    ``parallel=True``; all other jobs fall back to in-process sequential execution.
    """

    def __init__(self, dbname: str, worker_count: int):
        self.dbname = dbname
        assert worker_count > 1
        self.worker_count = worker_count
        self.pool: ProcessPoolExecutor | None = None

    def __getstate__(self):
        state = self.__dict__.copy()
        # `ProcessPoolExecutor` cannot be pickled
        # due to an internal thread.lock.
        # A subprocess doesn't need the pool anyway.
        state['pool'] = None
        return state

    def _subprocess_init(self):
        # SIGINT is handled by the parent process; subprocesses should exit immediately.
        # Use os._exit() instead of sys.exit() to avoid raising SystemExit,
        # which ProcessPoolExecutor's internals would catch, allowing the worker
        # to continue processing queued tasks. We want to prevent this since
        # abruptly terminated jobs can be resumed later anyway.
        signal.signal(signal.SIGINT, lambda *_: os._exit(0))

        # We cannot be certain that the multiprocessing is done via `fork` or `spawn`:
        # fork (Linux) -> re-uses the cached Registry for this db.
        # spawn (macOS/Windows) -> loads a new Registry and cache it. Acts as a pre-warm.
        Registry(self.dbname)
        _logger.info(
            "Worker %s initialized for database '%s'",
            os.getpid(),
            self.dbname,
        )

    def _subprocess_execute(self, job_id: int, context: dict):

        def execute_job():
            """
            Small wrapper to retry on additional database exceptions.
            
            Usually these exceptions are due to a user error,
            but in the context of populating with multiple workers,
            they're due to randomness, so we want to retry on them
            instead of failing the populate session.
            """
            try:
                job.execute()
            except PG_EXCEPTIONS_TO_RETRY as exc:
                error = psycopg2.errorcodes.lookup(exc.pgcode)

                msg = None
                if isinstance(exc, CheckViolation | ExclusionViolation):
                    msg = env._("Adapt the generator parameter to generate values within the constraint")
                if isinstance(exc, NotNullViolation):
                    msg = env._("The field is implicitly required, consider adding `null_frac=0`")
                if isinstance(exc, UniqueViolation):
                    msg = env._("Consider using a generator (or combination of) that produces more varied values")

                raise ConcurrencyError(f"{error} ({msg})" if msg else error) from exc

        registry = Registry(self.dbname)
        with registry.cursor() as cr:
            uid = context.setdefault('uid', SUPERUSER_ID)
            env = api.Environment(cr, uid, context)
            job = env['populate.job'].browse(job_id)

            assert job.exists()

            if job.context:
                job = job.with_context(job.context)

            retrying(execute_job, env)

    @staticmethod
    @contextmanager
    def from_session(session: Session) -> AbstractContextManager[ParallelExecutor]:
        executor = ParallelExecutor(session.env.cr.dbname, session.worker_count)
        try:
            _logger.info(
                "Creating worker pool with %d processes for database '%s'",
                session.worker_count,
                executor.dbname,
            )
            executor.pool = ProcessPoolExecutor(
                max_workers=executor.worker_count,
                initializer=executor._subprocess_init,
            )

            yield executor

        finally:
            if executor.pool:
                _logger.info("Shutting down worker pool...")
                executor.pool.shutdown(wait=True, cancel_futures=True)

    def execute(self, jobs: Job):
        for job in jobs:
            if job.child_ids and job.parallel:
                with job.execution_scope():
                    context = dict(job.env.context)
                    futures = {
                        self.pool.submit(
                            self._subprocess_execute, subjob.id, context,
                        ): subjob
                        for subjob in job.pending_subjobs
                    }

                    failures = []
                    for future in as_completed(futures):
                        subjob = futures[future]
                        try:
                            future.result()
                        except KeyboardInterrupt:
                            raise  # Will be caught at CLI level
                        except Exception as exc:  # noqa: BLE001
                            exc.add_note(job.env._("in Job %s", subjob.parent_path))
                            failures.append((subjob, exc))

                    if failures:
                        raise ExceptionGroup(
                            job.env._("%(count)s parallel job(s) failed", count=len(failures)),
                            [exc for _, exc in failures],
                        )
            else:
                job.execute()
