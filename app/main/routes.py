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


@bp.route('/redis-delete/<key>')
@login_required
def redis_del_key(key):
    try:
        current_app.redis.delete(key)
        Task.query.filter_by(id=key).delete()
        db.session.commit()
        data = jsonify('true')
    except Exception as e:
        current_app.logger.error(f'ERROR in redis_del_key route: {e}')
        data = abort(404)
    return data


@bp.route('/zip-delete/<key>')
@login_required
def del_zip(key):
    print(key)
    try:
        path = os.path.join(current_app.config["SAVE_ZIP"], key)
        os.remove(path)
        return jsonify('')
    except FileNotFoundError:
        return abort(404)


@bp.route('/get-zip/<string:filename>')
@login_required
def get_zip(filename):
    try:
        return send_from_directory(current_app.config["SAVE_ZIP"], path=filename, as_attachment=True)
    except FileNotFoundError:
        return abort(404)


@bp.route('/get/<string:key>')
@login_required
def get(key):
    """
    Args:
        key:
            key its filename
    Returns:
            Task.id
    """
    user_task = Task.query.filter(Task.user == current_user, Task.images, Images.filename == key).first()

    if user_task:
        data = {'task_id': user_task.id}
    else:
        return abort(404)

    return jsonify(data)


@bp.route('/progress/<task_id>', methods=['GET', 'POST'])
def progress(task_id):
    try:
        send = current_app.redis.get(task_id)

        # print('send in progress route: ', send)

        if send:
            # current_app.redis.delete(task.id)
            return jsonify({
                'name': 'task',
                'data': json.loads(send.decode("utf-8"))
            })
        else:
            return jsonify({
                'name': 'task',
                'data': {'in_queries': 'Please_wait'}
            })
    except Exception as e:
        current_app.logger.info(f"ERROR in progress rout: {e}")
        return abort(404)


@bp.route('/del/<prediction_id>')
@login_required
def delete(task_id):
    current_app.logger.info(f"user {current_user} delete predict id = {task_id}")
    # TODO
    # подумать нужно ли удалять задачи, если да добавить их в алгоритм удаления
    task = Task.query.filter_by(id=task_id).first()
    Predict.query.filter(Task, Task.id == task.id).delete()
    db.session.commit()
    data = True
    return jsonify(data)


@bp.route('/new_analysis/<image_id>')
@login_required
def new_analysis(image_id):
    current_app.logger.info(f'start new analysis, img_id: {image_id}')
    pred = Predict(image_id=image_id)
    db.session.add(pred)
    db.session.commit()
    # if current_user.get_task_in_progress('img_prediction'):
    #     flash('An predict task is currently in progress')
    # else:
    current_app.logger.info("start pred.lounch_task")
    pred.launch_task('img_prediction', 'make predict...')
    db.session.commit()
    return redirect(url_for('main.index', filename=f'{pred.id}'))


@bp.route('/')
@bp.route('/analysis')
@login_required
def analysis():
    # data = Images.query.order_by(Images.timestamp.desc()).all()
    # return render_template('get_analysis.html', title='analysis', body='')
    return redirect(url_for('main.cutting_rout_celery'))


@bp.route('/index/', defaults={'filename': None})
@bp.route('/index/<filename>', methods=['GET'])
@login_required
def index(filename):
    page = request.args.get('page', 1, type=int)

    if filename is None:
        id = request.args.get('select')

        if request.args.get('new_analysis'):
            print("redirect to new analysis")
            return redirect(url_for('main.new_analysis', image_id=id))

        if id is None:
            data = Predict.query.order_by(Predict.timestamp.desc()).paginate(page,
                                                                             current_app.config['POSTS_PER_PAGE'],
                                                                             False)
        elif id == 'history':
            data = Predict.query.order_by(Predict.timestamp.desc()).paginate(page,
                                                                             current_app.config['POSTS_PER_PAGE'],
                                                                             False)
        else:
            data = Predict.query.filter(Predict.images, Images.id == id) \
                .paginate(page,
                          current_app.config['POSTS_PER_PAGE'],
                          False)
        # print(data.items)
        if not data.items:
            flash(f'Нет выполненых исследованний')
        next_url = url_for('main.index', page=data.next_num) if data.has_next else None
        prev_url = url_for('main.index', page=data.prev_num) if data.has_prev else None
        return render_template('index.html', title='Analysis', body='', data=data.items,
                               next_url=next_url, prev_url=prev_url)

    elif filename.isdigit():
        data = Predict.query.filter_by(id=filename)
    else:
        img = Images.query.filter_by(filename=filename).first()
        predict = img.predict.filter(Predict.tasks, Task.complete is False)
        data = predict.order_by(Predict.timestamp.desc()).all()
    # for i in data:
    #     print(i)

    return render_template('index.html', title='Analysis', body='', data=data)


@bp.route('/upload', methods=['POST', 'GET'])
@login_required
def upload():
    if request.method == 'POST':
        img = file_save_and_add_to_db(request)

        predict = Predict(images=img,
                          timestamp=datetime.utcnow())

        path_to_save_draw_img = os.path.join(current_app.config['BASEDIR'],
                                             f"{current_app.config['DRAW']}/{img.filename}")

        if not os.path.exists(path_to_save_draw_img):
            os.mkdir(path_to_save_draw_img)

        current_user.launch_task(name='mk_pred',
                                 description=f'{img.filename} prediction',
                                 job_timeout=10800,
                                 img=img,
                                 predict=predict,
                                 medit=current_app.medit,
                                 )
        db.session.commit()

        return render_template('upload.html', title='Загрузка', body='')
    else:
        return render_template('upload.html', title='Загрузка', body='Выберите файл')


def file_save_and_add_to_db(request):
    files = request.files.getlist("file")
    if files:
        for file in files:
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            current_app.logger.info(f'получил файл {file.filename}')
            file.save(path)
            current_app.logger.info(f"сохранил файл {file.filename}")
            img = Images(path)
            if Images.query.filter_by(analysis_number=img.analysis_number).first() is None:
                db.session.add(img)
                db.session.commit()
                current_app.logger.info(f"{file.filename} saved to {current_app.config['UPLOAD_FOLDER']}")
            else:
                current_app.logger.info(f"{file.filename} already in bd")
            img = Images.query.filter_by(analysis_number=img.analysis_number).first()
            return img


@bp.route('/cutting', methods=['POST', 'GET'])
@login_required
def cut_rout():
    """
        Что мне надо?
        - отображать все задычи по порезке изображения пользователя
        - добавлять новую задачу в очередь
        - отображать статус задачи (выполняется или задача в очереди)
    Returns:

    """
    data = None
    try:
        if current_user.get_task_in_progress('img_cutt'):
            # data = current_user.get_task_in_progress('img_cutt')
            flash('now images is cutting')

        if request.method == 'POST':
            img = file_save_and_add_to_db(request)

            # Start new task
            current_user.launch_task(name='img_cutt',
                                     description=f'{img.filename} cutting',
                                     img=img,
                                     job_timeout=1800,
                                     path=img.file_path,
                                     CUTTING_FOLDER=current_app.config['CUTTING_FOLDER'],
                                     _CUT_IMAGE_SIZE=current_app.config['_CUT_IMAGE_SIZE'],
                                     )

            db.session.commit()
        return render_template('cut_rout_test.html', title='Порезка SVS', body=data)

    except Exception as e:
        current_app.logger.error(e)


@bp.route('/cutting_celery', methods=['POST', 'GET'])
@login_required
def cutting_rout_celery():
    try:
        data = None
        if current_user.get_task_in_progress('img_cutt'):
            data = current_user.get_task_in_progress('img_cutt')
            flash('now images is cutting')
        if request.method == 'GET':
            return render_template('cut_rout.html', title='Порезка SVS', body=data)
        if request.method == 'POST':
            img = file_save_and_add_to_db(request)
            from app.celery_task.celery_task import cutting_task
            celery_job = cutting_task.apply_async()

            task = Task(id=celery_job.id,
                        name='img_cutt',
                        description=f'Cutting {img.filename}',
                        user=current_user,
                        images=img)
            db.session.add(task)
            db.session.commit()
            return jsonify({'task_id': task.id}), 202, {'Location': url_for('main.taskstatus', task_id=task.id)}
        return render_template('cut_rout.html', title='Порезка SVS', body=data)

    except Exception as e:
        current_app.logger.error(e)


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
            'all_mitoz': task.info.get('all_mitoz', ''),
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

            img = file_save_and_add_to_db(request)
            predict = Predict(images=img,
                              timestamp=datetime.utcnow())
            from app.celery_task.celery_task import make_predict_task
            celery_job = make_predict_task.apply_async()

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
