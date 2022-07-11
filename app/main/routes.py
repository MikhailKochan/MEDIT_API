from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app
from flask_login import current_user, login_required
from app import db
import os
from app.models import Images, Predict
from app.main import bp


@bp.route('/')
@bp.route('/analysis')
@login_required
def analysis():
    data = Images.query.order_by(Images.timestamp.desc()).all()
    return render_template('analysis.html', title='analysis', body='', data=data)


@bp.route('/index', defaults={'filename': None})
@bp.route('/index/<filename>', methods=['GET', 'POST'])
@login_required
def index(filename):
    sendata = []
    data = [{'data': 'data', 'name': 'name', 'status': 'status',
             'result': 'result', 'href': '#', 'href_zip_auto': '/'},
            {'data': 'data', 'name': 'name', 'status': 'status',
             'result': 'result', 'href': '#', 'href_zip_auto': '/'}]
    page = request.args.get('page', 1, type=int)

    if filename == None:
        id = request.args.get('select')
        if id == None:
            data = Predict.query.order_by(Predict.timestamp.desc()).paginate(page, current_app.config['POSTS_PER_PAGE'], False)
        elif id == 'history':
            data = Predict.query.order_by(Predict.timestamp.desc()).paginate(page, current_app.config['POSTS_PER_PAGE'], False)
        else:
            data = Predict.query.filter_by(id=id).paginate(page, current_app.config['POSTS_PER_PAGE'], False)
        next_url = url_for('main.index', page=data.next_num) if data.has_next else None
        prev_url = url_for('main.index', page=data.prev_num) if data.has_prev else None
        return render_template('index.html', title='Analysis', body='', data=data.items,
                               next_url=next_url, prev_url=prev_url)
    else:
        data = Predict.query.filter_by()
        return render_template('index.html', title='Analysis', body='', data=data)


@bp.route('/upload', methods=['POST', 'GET'])
@login_required
def upload():
    if request.method == 'POST':
        files = request.files.getlist("file")
        if files:
            for file in files:
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename))
                current_app.logger.info(f"{file.filename} saved to {current_app.config['UPLOAD_FOLDER']}")
        return render_template('upload.html', title='Загрузка', body='')
    else:
        return render_template('upload.html', title='Загрузка', body='Выберите файл')


@bp.route('/predict', methods=['POST', 'GET'])
def pred():
    predictor = current_app.extensions['predictor']
    if predictor:
        print(predictor)
        x = "True"
    else:
        x = "False"
    return x
