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
from project.models import User, Version, Category
from .forms import AddCategoryForm
import traceback


# CONFIG
maintenance_blueprint = Blueprint('maintenance', __name__, 
                                  template_folder='templates',
                                  url_prefix='/maintenance')

TASKS = Category.TASKS()

# ROUTES
@maintenance_blueprint.route('/index')
def index():
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.get_first()
    if version is None:
        abort(404)
    return redirect(url_for('maintenance.categs_list', selected=version.name))

@maintenance_blueprint.route('/categs_list/<selected>')
@login_required
def categs_list(selected):   
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    categs = {}
    for task in TASKS:
        categs[task[0]] = Category.list(task[0], version.name)
    return render_template('maintenance/index.html', 
                           version=version, categs=categs, tasks=dict(TASKS))

@maintenance_blueprint.route('/category/add/<task_id>', methods=['GET', 'POST'])
@login_required
def categ_add(task_id):
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        abort(400)
    if version.status in [3]:
        message = Markup(
            "<strong>Warning!</strong> Unable to add category to committed version. ")
        flash(message, 'warning')
        return redirect(url_for('maintenance.categs_list', 
                                selected=version.name))
    form = AddCategoryForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                categ = Category(form.name.data,
                                 version.id,
                                 task_id)
                db.session.add(categ)
                db.session.commit()
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('maintenance.categs_list', 
                                        selected=version.name))
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to save this category. " + str(e))
                flash(message, 'danger')
    return render_template('maintenance/add_categ.html', 
                           form=form,
                           task_id=task_id,
                           selected=version.name)

@maintenance_blueprint.route('/models_list/<selected>')
@login_required
def models_list(selected):    
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    models = []
    return render_template('maintenance/models_list.html', 
                           version=version, models=models)    
