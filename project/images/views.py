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
import traceback

from project import app, db, mail
from project.models import User, Version


# CONFIG
images_blueprint = Blueprint('images', __name__, 
                             template_folder='templates',
                             url_prefix='/images')


# ROUTES
@images_blueprint.route('/index')
@login_required
def index():
    if 'selected_version' in session:
        first_one = Version.query.filter_by(name=session['selected_version']).first()
    else:
        first_one = Version.get_first()
    if first_one is None:
        abort(404)
    return redirect(url_for('images.browse', selected=first_one.name))

@images_blueprint.route('/browse/<selected>')
@login_required
def browse(selected):    
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    return render_template('images/index.html', version=version)    