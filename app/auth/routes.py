from flask import render_template, redirect, url_for, flash, request
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user
from app.auth import bp
from app.auth.forms import LoginForm
from app.models import User


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.predict_rout'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.predict_rout'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неправильное имя пользователя или пароль')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.predict_rout')
        return redirect(next_page)
    return render_template('auth/login.html', title='Вход', form=form)
