from celery import current_app as current_celery_app


def make_celery(app):
    celery = current_celery_app
    celery.config_from_object(app.config, namespace="CELERY")

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

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
            # if current_app:
            #     current_app.logger.error(e)
            # db.session.rollback()
