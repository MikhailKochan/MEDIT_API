from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app, abort
from flask import send_from_directory
from flask_login import current_user, login_required
from app import db
import os
from app.models import Images, Predict, Status, Task
from app.main import bp
from sqlalchemy.dialects.sqlite import insert
import json
from rq import get_current_job
from rq import Retry
from app.view import file_save_and_add_to_db
from app.celery_task.celery_task import make_predict_task, cutting_task, error_handler


@bp.route('/history', methods=['GET', 'POST'])
def history():
    # if request.method == 'GET':
    return render_template('history.html', title='История исследований')


@bp.route('/info', methods=['GET', 'POST'])
def info():
    # if request.method == 'GET':
    return render_template('info.html', title='О программе')


@bp.route('/get-zip/<string:filename>')
@login_required
def get_zip(filename):
    try:
        return send_from_directory(current_app.config["SAVE_ZIP"], path=filename, as_attachment=True)
    except FileNotFoundError:
        return abort(404)


@bp.route('/progress/<task_id>', methods=['GET', 'POST'])
def progress(task_id):
    try:
        send = current_app.redis.get(task_id)
        if send:
            return jsonify(json.loads(send.decode("utf-8")))
        else:
            return jsonify({'state': 'PENDING'})
    except Exception as e:
        current_app.logger.info(f"ERROR in progress rout: {e}")
        return abort(404)


@bp.route('/')
@bp.route('/predict', methods=['POST', 'GET'])
@login_required
def predict_rout():
    tasks = None
    if current_user.get_task_in_progress('mk_pred'):
        tasks = current_user.get_task_in_progress('mk_pred')
        flash(f'Количество исследований в работе: {len(tasks)}')
    if request.method == 'GET':
        return render_template('get_analysis.html', title='Исследование', tasks=tasks)
    if request.method == 'POST':
        img = file_save_and_add_to_db(request)
        if img is None:
            return render_template('get_analysis.html', title='Исследование', tasks=tasks)
        predict = Predict(images=img, timestamp=datetime.utcnow())

        path_to_save_draw_img = os.path.join(current_app.config['BASEDIR'],
                                             f"{current_app.config['DRAW']}/{img.filename}")

        if not os.path.exists(path_to_save_draw_img):
            os.mkdir(path_to_save_draw_img)

        task = current_user.launch_task(name='mk_pred',
                                        description=f'{img.filename} prediction',
                                        job_timeout=10800,
                                        img=img,
                                        predict=predict,
                                        medit=current_app.medit,
                                        )
        db.session.commit()

        return jsonify({'task_id': task.id}), 202, {'Location': url_for('main.progress', task_id=task.id)}


@bp.route('/cutting_celery', methods=['POST', 'GET'])
@login_required
def cutting_rout_celery():
    tasks = None
    try:
        if current_user.get_task_in_progress('img_cutt'):
            tasks = current_user.get_task_in_progress('img_cutt')
            flash(f'now {len(tasks)} images in cutting')
        if request.method == 'POST':
            img = file_save_and_add_to_db(request)
            if img:
                celery_job = cutting_task.apply_async(link_error=error_handler.s(),
                                                      kwargs={'img_id': img.id})

                task = Task(id=celery_job.id,
                            name='img_cutt',
                            description=f'Cutting {img.filename}',
                            user=current_user,
                            images=img)

                db.session.add(task)

                db.session.commit()
                return jsonify({'task_id': task.id}), 202, {'Location': url_for('main.taskstatus', task_id=task.id)}
    except Exception as e:
        current_app.logger.error(e)
    return render_template('cut_rout.html', title='Порезка SVS', tasks=tasks)


@bp.route('/status/<task_id>')
def taskstatus(task_id):
    from app.celery_task.celery_task import cutting_task
    task = cutting_task.AsyncResult(task_id)
    # print(task.info)
    # print(dir(task))
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'progress': 0,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'progress': task.info.get('progress', 0),
            'function': task.info.get('function', ''),
            'filename': task.info.get('filename', ''),
            'all_mitoz': task.info.get('all_mitoz'),
            'analysis_number': task.info.get('analysis_number', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'progress': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


@bp.route('/predict_celery', methods=['POST', 'GET'])
@login_required
def predict_rout_celery():
    try:
        data = None
        if current_user.get_task_in_progress('img_predict'):
            data = current_user.get_task_in_progress('img_predict')
            flash('now images in predict')
        if request.method == 'GET':
            return render_template('make_predict.html', title='analysis', body=data)
        if request.method == 'POST':
            img = file_save_and_add_to_db(request, do_predict=True)

            predict = Predict(images=img,
                              timestamp=datetime.utcnow(),
                              path_to_save=os.path.join(current_app.config.BASEDIR,
                                                        current_app.config.DRAW,
                                                        img.filename,
                                                        datetime.utcnow().strftime('%d_%m_%Y__%H_%M')))

            celery_job = make_predict_task.apply_async(link_error=error_handler.s(),
                                                       kwargs={'img': img, 'predict': predict})

            task = Task(id=celery_job.id,
                        name='img_predict',
                        description=f'Predict {img.filename}',
                        user=current_user,
                        images=img,
                        predict=predict)
            db.session.add(predict)
            db.session.add(task)
            db.session.commit()
            return jsonify({'task_id': task.id}), 202, {'Location': url_for('main.taskstatus', task_id=task.id)}
        return render_template('make_predict.html', title='Порезка SVS', body=data)

    except Exception as e:
        current_app.logger.error(e)
