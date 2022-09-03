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


@bp.route('/debug-sentry')
def trigger_error():
    division_by_zero = 1 / 0


@bp.route('/get-zip/<string:filename>')
@login_required
def get_zip(filename):
    try:
        return send_from_directory(current_app.config["SAVE_ZIP"], path=filename, as_attachment=True)
    except FileNotFoundError:
        return abort(404)
    # img = Images.query.filter_by(filename=key).first()
    # if img:
    #     data = img.id
    # else:
    #     data = abort(404)
    # return jsonify(data)


@bp.route('/get/<string:key>')
@login_required
def get(key):
    print('key in /get', key)
    img = Images.query.filter_by(filename=key).first()
    user_tasks = current_user.get_tasks_in_progress()
    if img:
        task = img.tasks.all()
        if task:
            img_task = task[-1]
            data = {'image_id': img.id,
                    'task_id': img_task.id}
        else:
            data = img.id
    elif user_tasks:
        data = {'task_id': user_tasks[0].id}
    else:
        data = abort(404)

    return jsonify(data)


@bp.route('/progress/<task_id>', methods=['GET', 'POST'])
def progress(task_id):
    send = current_app.redis.get(task_id)
    if send:
        # current_app.redis.delete(task.id)
        return jsonify({
            'name': 'task',
            'data': json.loads(send.decode("utf-8"))
        })
    else:
        abort(404)


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
    data = Images.query.order_by(Images.timestamp.desc()).all()
    return render_template('analysis.html', title='analysis', body='', data=data)


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
        files = request.files.getlist("file")
        if files:
            for file in files:
                path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
                file.save(path)
                img = Images(path)
                if Images.query.filter_by(analysis_number=img.analysis_number).first() is None:
                    db.session.add(img)
                    db.session.commit()
                    current_app.logger.info(f"{file.filename} saved to {current_app.config['UPLOAD_FOLDER']}")
                else:
                    current_app.logger.info(f"{file.filename} already in bd")

        return render_template('upload.html', title='Загрузка', body='')
    else:
        return render_template('upload.html', title='Загрузка', body='Выберите файл')


@bp.route('/cutting', methods=['POST', 'GET'])
@login_required
def cut_rout():
    if current_user.get_task_in_progress('img_cutt'):
        flash('now images in cutting')
    else:
        try:
            if request.method == 'POST':
                files = request.files.getlist("file")

                if files:
                    # for file in files:
                    file = files[0]

                    path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
                    current_app.logger.info(f'получил файл {file.filename}')
                    file.save(path)
                    current_app.logger.info(f"сохранил файл {file.filename}")

                    current_user.launch_task(name='img_cutt',
                                             description=f'{file.filename} cutting',
                                             path=path,
                                             )
                    # rq_job = current_app.task_queue.enqueue('app.new_tasks.img_cutt', path, job_timeout=1800)
                    #
                    # task = Task(id=rq_job.get_id(), name="app.new_tasks.img_cutt",
                    #             description=f"start cutting img {file.filename}",
                    #             )
                    #
                    # db.session.add(task)

                    db.session.commit()

        except Exception as e:
            current_app.logger.error(e)
        return render_template('cut_rout.html', title='Загрузка', body='Выберите файл')
