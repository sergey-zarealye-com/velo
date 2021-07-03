# project/users/views.py

# IMPORTS
from flask import render_template, Blueprint, request, redirect, url_for, flash, Markup, abort
from sqlalchemy.exc import IntegrityError
from flask_login import login_user, current_user, login_required, logout_user
from itsdangerous import URLSafeTimedSerializer
from threading import Thread
from flask_mail import Message
from datetime import datetime, timedelta

from project import app, db, mail
from project.models import User, Version, Category


# CONFIG
maintenance_blueprint = Blueprint('maintenance', __name__, 
                                  template_folder='templates',
                                  url_prefix='/maintenance')


# ROUTES
@maintenance_blueprint.route('/index')
def index():
    first_one = Version.get_first()
    if first_one is None:
        abort(404)
    return redirect(url_for('maintenance.categs_list', selected=first_one.name))

@maintenance_blueprint.route('/categs_list/<selected>')
@login_required
def categs_list(selected):    
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    categs = Category.query.filter_by(version_id=version.id)
    return render_template('maintenance/index.html', 
                           version=version, categs=categs)    

@maintenance_blueprint.route('/models_list/<selected>')
@login_required
def models_list(selected):    
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    models = []
    return render_template('maintenance/models_list.html', 
                           version=version, models=models)    
