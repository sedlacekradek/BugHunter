from flask import Blueprint, render_template, redirect, url_for, flash
from . import db, mail
from .models import User
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .forms import RegistrationForm, LoginForm, ResetForm, NewPasswordForm, ChangePasswordForm
from flask_mail import Message
from time import time
import jwt
import os


### SETUP ###
JWT_SECRET = os.getenv("WT_SECRET")
auth = Blueprint("auth", __name__)


### AUTH FUNCTIONS ###
@auth.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                flash("Logged in.", category="success")
                login_user(user, remember=True)
                return redirect(url_for("views.home"))
            else:
                flash("Password not correct.", category="error")
        else:
            flash("User does not exist.", category="error")
    return render_template("login.html", form=form, active="login")

### AUTH FUNCTIONS ###
@auth.route("/demo", methods=["GET", "POST"])
def demo_user():
    user = User.query.filter_by(email="demo@demo.demo").first()
    flash("Logged in.", category="success")
    login_user(user, remember=True)
    return redirect(url_for("views.home"))


@auth.route("/signup", methods=["GET", "POST"])
def signup():
    form = RegistrationForm()
    if form.validate_on_submit():
        # noinspection PyArgumentList
        # PyCharm bug - doesn't recognize column names as arguments when using mixins
        user = User(email=form.email.data, username=form.name.data,
                    password=generate_password_hash(form.password.data, method="sha256"))
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        flash('User created.', category="success")
        return redirect(url_for("views.home"))
    return render_template('signup.html', form=form, active="signup")


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Successfully logged out.", category="success")
    return redirect(url_for("auth.login"))


@login_required
@auth.route("/password-change", methods=['GET', 'POST'])
def change_password():
    form = ChangePasswordForm()
    user = current_user
    if form.validate_on_submit():
        if check_password_hash(user.password, form.old_password.data):
            user.password = generate_password_hash(form.password.data, method="sha256")
            db.session.commit()
            flash('Password has been changed.', category="success")
            return redirect(url_for('views.home'))
        else:
            flash('Old password not correct.', category="error")
    return render_template('change-pw.html', form=form)


### PASSWORD RESET ###
def get_reset_token(user, expires=500):
    """
    takes user and generates expiring secret token used to verify the user
    """
    return jwt.encode({'reset_password': user.username, 'exp': time() + expires},
                      key=JWT_SECRET)


def verify_reset_token(token):
    """
    takes secret token and decodes it to get username
    """
    username = jwt.decode(token, key=JWT_SECRET, algorithms="HS256")['reset_password']
    return User.query.filter_by(username=username).first()


@auth.route("/password-reset", methods=["GET", "POST"])
def password_reset():
    """
    user fills in their email address and receives a mail with a secret link
    """
    form = ResetForm()
    if form.validate_on_submit():
        flash('Mail has been sent.', category="success")
        user = User.query.filter_by(email=form.email.data).first()
        token = get_reset_token(user=user)
        mail_content = render_template('reset-email.html', token=token)
        msg = Message(subject="BugHunter - password reset", html=mail_content, recipients=[user.email])
        mail.send(msg)
        return redirect(url_for("auth.login"))
    return render_template('reset-pw.html', form=form)


@auth.route("/password-reset-verified/<token>", methods=['GET', 'POST'])
def reset_verified(token):
    """
    when user follows link from the mail, they land on a page where they can change to password
    """
    form = NewPasswordForm()
    if form.validate_on_submit():
        user = verify_reset_token(token)
        user.password = generate_password_hash(form.password.data, method="sha256")
        db.session.commit()
        flash('Password has been changed.', category="success")
        return redirect(url_for('auth.login'))
    return render_template('reset-verified.html', form=form)
