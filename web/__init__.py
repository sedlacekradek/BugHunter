from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import secrets
from flask_mail import Mail
from flask_ckeditor import CKEditor
from dotenv import load_dotenv
import os


load_dotenv()
mail = Mail()
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = secrets.token_hex(16)
    app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024  # max upload size 3MB

    # database config
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
    db.init_app(app)

    # mail config
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")
    app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
    app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
    mail.init_app(app)

    # rich text editor
    ckeditor = CKEditor()
    ckeditor.init_app(app)

    # models
    from .models import User, Project, Ticket, Comment, Like, UserMessage, UserNotification
    with app.app_context():
        db.create_all()
        db.session.commit()

    # blueprints
    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")

    # login manager
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # jinja custom filters
    @app.template_filter("datetime_format")
    def datetime_format(value, format="%d-%m-%y %H:%M"):
        return value.strftime(format)

    return app