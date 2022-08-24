from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app, abort
from flask_login import current_user, login_required
from app import db
import os
from app.models import Images, Predict, Status, Task
from app.main import bp
from sqlalchemy.dialects.sqlite import insert
import json


@bp.route('/debug-sentry')
def trigger_error():
    division_by_zero = 1 / 0


@bp.route('/get/<string:key>')
@login_required
def get(key):
    img = Images.query.filter_by(filename=key).first()
    if img:
        data = img.id
    # if redis_cache.exists(key):
    #     data = redis_cache.get(key).decode("utf-8")
    #
    else:
        data = abort(404)
    return jsonify(data)


@bp.route('/progress/<prediction_id>', methods=['GET'])
@login_required
def progress(prediction_id):
    task = Task.query.filter_by(predict_id=prediction_id).first()
    send = current_app.redis.get(task.id)
    if send:
        return jsonify([{
            'name': 'task',
            'data': json.loads(send.decode("utf-8"))
        }])
    else:
        abort(404)


@bp.route('/del/<prediction_id>')
@login_required
def delete(prediction_id):
    current_app.logger.info(f"user {current_user} delete predict id = {prediction_id}")
    #TODO
    #подумать нужно ли удалять задачи, если да добавить их в алгоритм удаления
    # task = Task.query.filter_by(predict_id=prediction_id).first()
    Predict.query.filter_by(id=prediction_id).delete()
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
    # print(request.args)

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
                print(f'file {file} save to {path}')
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


@bp.route('/predict', methods=['POST', 'GET'])
def pred():
    predictor = current_app.medit.predictor
    if predictor:
        print(predictor)
        x = "True"
    else:
        x = "False"
    return x
