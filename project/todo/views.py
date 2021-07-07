# project/users/views.py

# IMPORTS
from flask import render_template, Blueprint, request, redirect, url_for
from flask import flash, Markup, abort, session
from sqlalchemy.exc import IntegrityError
from flask_login import login_user, current_user, login_required, logout_user
from itsdangerous import URLSafeTimedSerializer
from threading import Thread
from flask_mail import Message
from datetime import datetime, timedelta

from project import app, db, mail
from project.models import User, Version


# CONFIG
todo_blueprint = Blueprint('todo', __name__, 
                           template_folder='templates',
                           url_prefix='/todo')


# ROUTES
@todo_blueprint.route('/list')
def list():
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.query.filter_by(name=selected).first()

    return render_template('todo/list.html')
