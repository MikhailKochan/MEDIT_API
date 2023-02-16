import datetime
import os

from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app, abort
from flask import send_from_directory
from flask_login import current_user, login_required
from app import db

from app.models import Images, Predict, Settings, Task
from app.main.forms import SearchPredictForm, SettingsForm, PredictForm

from app.main import bp

import json
import zipfile

from app.view import check_req, file_name_maker, check_zip
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


@bp.route('/cutting_celery', methods=['POST', 'GET'])
@login_required
def cutting_rout_celery():
    tasks = None
    try:
        if current_user.get_task_in_progress('img_cutt'):
            tasks = current_user.get_task_in_progress('img_cutt')
            flash(f'now {len(tasks)} images in cutting')
        # if request.method == 'POST':
            # img = file_save_and_add_to_db(request)
            # if img:
            #     celery_job = cutting_task.apply_async(link_error=error_handler.s(),
            #                                           kwargs={'img_id': img.id})
            #
            #     task = Task(id=celery_job.id,
            #                 name='img_cutt',
            #                 description=f'Cutting {img.filename}',
            #                 user=current_user,
            #                 images=img)
            #
            #     db.session.add(task)
            #
            #     db.session.commit()
            #     return jsonify({'task_id': task.id}), 202, {'Location': url_for('main.taskstatus', task_id=task.id)}
    except Exception as e:
        current_app.logger.error(e)
    return render_template('cut_rout.html', title='Порезка SVS', tasks=tasks)


@bp.route('/predict', methods=['POST', 'GET'])
@login_required
def predict_rout_celery():
    try:
        # print('g.test_server_connect:', g.test_server_connect)
        access = 0  # время до следующей задачи
        tasks = current_user.get_my_tasks()
        task_in_process = [task for task in tasks if task.complete is False]
        delay = current_user.settings.user_reloading_time  # пауза между задачами заданная в настройках пользователя
        if tasks:
            next_task_time = tasks[0].timestamp + datetime.timedelta(seconds=delay)
            dt = next_task_time - datetime.datetime.utcnow()
            if dt.days < 0:
                pass
            else:
                access = dt.seconds  # время до следующей задачи
        form = PredictForm()
        if request.method == 'POST' and access == 0:
            files = request.files.getlist("file")
            for file in files:
                current_app.logger.info(f'получил файл {file.filename}')
                filename = file_name_maker(file.filename)
                path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

                file.save(path)
                current_app.logger.info(f"сохранил файл {filename}")

                if (zipfile.is_zipfile(path) and check_zip(path)) \
                        or filename.endswith(tuple(current_app.config['IMAGE_FORMAT'])):

                    celery_job = make_predict_task.apply_async(link_error=error_handler.s(),
                                                               kwargs={'user_id': current_user.id,
                                                                       'path_file': path})

                    return jsonify({'task_id': celery_job.id}), 202, {'Location': url_for('main.taskstatus',
                                                                                          task_id=celery_job.id)}
                else:
                    os.remove(path)
                    current_app.logger.info(f"файл {filename} не подходит, и был удален")

        return render_template('get_analysis.html',
                               title='Исследование',
                               tasks=task_in_process,
                               access=access,
                               pause_delay=delay,
                               server_connect=g.test_server_connect,
                               form=form,
                               )
    except Exception as e:
        current_app.logger.error(e)


@bp.route('/status/<task_id>')
def taskstatus(task_id):
    from app.celery_task.celery_task import make_predict_task
    task = make_predict_task.AsyncResult(task_id)
    # print(task.info)
    # print(dir(task))
    if task:
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


@bp.before_request
@login_required
def test_ml_server_connect():
    # проверяем функцию, которая обрабатывает текущий URL
    # print('we in test connect before')
    # print(request.endpoint)
    if request.endpoint in ['main.predict_rout_celery']:
        # если это `predict_rout_celery`
        test_server_connect = getattr(g, 'test_server_connect', None)
        if test_server_connect is None and current_user:
            g.test_server_connect = current_user.test_server_ml()
