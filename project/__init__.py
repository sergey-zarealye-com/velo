# IMPORTS
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_login import login_required
from flask_mail import Mail
from flask_migrate import Migrate
import os

# CONFIG
import config

app = Flask(__name__, instance_relative_config=True)
# celery_app.config.from_object(os.environ['APP_SETTINGS'])
app.config.from_object(config.DevelopmentConfig)
app.logger.setLevel(config.DevelopmentConfig.LOG_LEVEL)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "users.login"

from project.models import User


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter(User.id == int(user_id)).first()


# BLUEPRINTS
from project.users.views import users_blueprint
from project.datasets.views import datasets_blueprint
from project.images.views import images_blueprint
from project.todo.views import todo_blueprint
from project.maintenance.views import maintenance_blueprint
from project.deduplication.views import dedup_blueprint

app.register_blueprint(users_blueprint)
app.register_blueprint(datasets_blueprint)
app.register_blueprint(images_blueprint)
app.register_blueprint(todo_blueprint)
app.register_blueprint(maintenance_blueprint)
app.register_blueprint(dedup_blueprint)


# ROUTES
@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    """Render homepage"""

    return render_template('home.html')


# ERROR PAGES
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def page_forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(410)
def page_gone(e):
    return render_template('410.html'), 410
