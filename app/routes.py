# -*- coding: utf-8 -*-
from flask import url_for, request, render_template, flash, send_from_directory, abort, jsonify, make_response, redirect
from app import app
from app.forms import LoginForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Images, Predict
from werkzeug.urls import url_parse
import os
import datetime


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/')
@app.route('/analysis')
@login_required
def analysis():
    data = Images.query.order_by(Images.timestamp.desc()).all()
    return render_template('analysis.html', title='analysis', body='', data=data)


@app.route('/index', defaults={'filename': None})
@app.route('/index/<filename>', methods=['GET', 'POST'])
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
            data = Predict.query.order_by(Predict.timestamp.desc()).paginate(page, app.config['POSTS_PER_PAGE'], False)
        elif id == 'history':
            data = Predict.query.order_by(Predict.timestamp.desc()).paginate(page, app.config['POSTS_PER_PAGE'], False)
        else:
            data = Predict.query.filter_by(id=id).paginate(page, app.config['POSTS_PER_PAGE'], False)
        next_url = url_for('index', page=data.next_num) if data.has_next else None
        prev_url = url_for('index', page=data.prev_num) if data.has_prev else None
        return render_template('index.html', title='Analysis', body='', data=data.items,
                               next_url=next_url, prev_url=prev_url)
    else:
        data = Predict.query.filter_by()
        return render_template('index.html', title='Analysis', body='', data=data)


@app.route('/upload', methods=['POST', 'GET'])
@login_required
def upload():
    if request.method == 'POST':
        files = request.files.getlist("file")
        if files:
            for file in files:
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
                app.logger.info(f"{file.filename} saved to {app.config['UPLOAD_FOLDER']}")
        return render_template('upload.html', title='Загрузка', body='')
    else:
        return render_template('upload.html', title='Загрузка', body='Выберите файл')
