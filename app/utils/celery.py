from celery import current_app as current_celery_app, Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


def make_celery(app):
    celery = current_celery_app
    celery.config_from_object(app.config, namespace="CELERY")
    TaskBase = celery.Task

    from app import db
    from app.view import Medit

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():

                # engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], convert_unicode=True)
                # db_sess = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))
                # db.session = db_sess
                # medit = Medit()
                # medit.init_app(app)

                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask

    return celery


def _set_celery_task_progress(job, progress, all_mitoz=None, func=None, filename=None, analysis_number=None):
    if job:
        try:
            job.update_state(state='PROGRESS',
                             meta={'progress': progress,
                                   'function': func,
                                   'filename': filename,
                                   'all_mitoz': all_mitoz,
                                   'analysis_number': analysis_number})

        except Exception as e:
            print(f'ERROR in set_celery_task_progress: {e}')
            if current_app:
                current_app.logger.error(e)


class DatabaseTask(Task):
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = Database.connect()
        return self._db
