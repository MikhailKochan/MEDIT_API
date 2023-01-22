from celery import current_app as current_celery_app, Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


def make_celery(app):
    celery = current_celery_app
    celery.config_from_object(app.config, namespace="CELERY")
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask

    return celery


def _set_celery_task_progress(job, **kwargs):
    if job:
        try:
            # task_id = job.request.id
            # task = job.AsyncResult(task_id)
            meta = {}
            # meta['progress'] = progress
            meta.update(kwargs)
            job.update_state(state='PROGRESS', meta=meta)

        except Exception as e:
            print(f'ERROR in set_celery_task_progress: {e}')


class DatabaseTask(Task):
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = Database.connect()
        return self._db
