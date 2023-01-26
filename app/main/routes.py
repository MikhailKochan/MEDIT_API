from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app, abort
from flask import send_from_directory
from flask_login import current_user, login_required
from app import db

from app.models import Images, Predict, Settings, Task
from app.main.forms import SearchPredictForm, SettingsForm
from app.main import bp

import json

from app.view import file_save_and_add_to_db, check_req
from app.celery_task.celery_task import make_predict_task, cutting_task, error_handler


@bp.route('/history', methods=['GET', 'POST'])
@login_required
def history():
    form = SearchPredictForm()
    sort = request.args.get('sort', '', type=str)
    page = request.args.get('page', 1, type=int)
    analysis_number = form.data.get('analysis_number')
    data = Predict.query.filter(Predict.tasks,
                                Task.complete == True,
                                Task.user_id == current_user.id)

    if form.validate_on_submit():
        if analysis_number:
            data = data.join(Images).filter_by(analysis_number=analysis_number)
    if sort:
        if sort == 'name':
            data = data.join(Images).order_by(Images.filename.desc())
        elif sort == 'date':
            data = data.order_by(Predict.timestamp.desc())
        elif sort == 'analysis_number':
            data = data.join(Images).order_by(Images.analysis_number.desc())
        elif sort == 'mitoses':
            data = data.order_by(Predict.result_all_mitoz.desc())

    data = data.paginate(page, current_app.config['POSTS_PER_PAGE'], False)

    if len(data.items) == 0:
        if analysis_number:
            flash(f'У Вас нет исследованний с номером {analysis_number}')
        else:
            flash(f'Нет выполненых исследованний')
    # if request.method == 'GET':
    next_url = url_for('main.history', page=data.next_num) if data.has_next else None
    prev_url = url_for('main.history', page=data.prev_num) if data.has_prev else None
    return render_template('predict_history.html', title='История исследований', data=data.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@bp.route('/info', methods=['GET', 'POST'])
def info():
    return render_template('info.html', title='О программе')


@bp.route('/logo', methods=['GET', 'POST'])
def logo():
    return send_from_directory(current_app.config["LOGO_PATH"], path='mitoz_ai.png', as_attachment=True)


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    default = Settings.get_default_settings()

    user_settings = current_user.get_settings()

    if request.method == "POST":
        req = request.form.to_dict()
        req = check_req(req)
        width = req['cutting_images_width'] if req['cutting_images_width'] else None
        height = req['cutting_images_height'] if req['cutting_images_height'] else None
        if width is not None and height is not None:
            user_settings.cutting_images_size = json.dumps((int(width), int(height)))

        # convert RGB2BGR
        BGR_rectangle = [int(req['blue_rectangle']), int(req['green_rectangle']), int(req['red_rectangle'])]
        BGR_text = [int(req['blue_text']), int(req['green_text']), int(req['red_text'])]

        user_settings.color_for_draw_rectangle = json.dumps(BGR_rectangle)
        user_settings.color_for_draw_text = json.dumps(BGR_text)

        user_settings.percentage_black = int(req['percent_black']) if req['percent_black'] else 10
        user_settings.percentage_white = int(req['percent_white']) if req['percent_white'] else 30
        db.session.add(user_settings)
        db.session.commit()
        flash('Ваши настройки были изменены')
        return render_template('settings.html', title='Настройки', settings=user_settings, default_set=default)

    if request.method == 'GET':
        return render_template('settings.html', title='Настройки', settings=user_settings, default_set=default)


@bp.route('/get-zip/<string:filename>')
@login_required
def get_zip(filename):
    try:
        if filename[:-4] != '.zip':
            filename = f'{filename}.zip'
        print('filename in get-zip', filename)
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
    from app.celery_task.celery_task import make_predict_task
    task = make_predict_task.AsyncResult(task_id)
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
            'all_mitoses': task.info.get('all_mitoses'),
            'analysis_number': task.info.get('analysis_number', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'progress': 0,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


@bp.route('/predict_celery', methods=['POST', 'GET'])
@login_required
def predict_rout_celery():
    try:
        tasks = None
        if current_user.get_task_in_progress('img_predict'):
            tasks = current_user.get_task_in_progress('img_predict')
            flash(f'Количество исследований в работе: {len(tasks)}')
        if request.method == 'GET':
            return render_template('get_analysis.html', title='Исследование', tasks=tasks)
        if request.method == 'POST':
            img = file_save_and_add_to_db(request)

            celery_job = make_predict_task.apply_async(link_error=error_handler.s(),
                                                       kwargs={'img': img.id,
                                                               'settings': current_user.get_settings().id})

            task = Task(id=celery_job.id,
                        name='img_predict',
                        description=f'Predict {img.filename}',
                        user=current_user,
                        images=img,
                        )

            db.session.add(task)
            db.session.commit()
            current_app.logger.info(f"task {task.id} add to bd")
            return jsonify({'task_id': task.id}), 202, {'Location': url_for('main.taskstatus', task_id=task.id)}

    except Exception as e:
        current_app.logger.error(e)
