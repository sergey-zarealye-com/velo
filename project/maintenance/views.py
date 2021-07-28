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
from .forms import AddCategoryForm, EditCategoryForm
import traceback
import difflib


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
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))
    return redirect(url_for('maintenance.categs_list', selected=version.name))

@maintenance_blueprint.route('/categs_list/<selected>')
@login_required
def categs_list(selected):   
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.query.filter_by(name=selected).first()
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))
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
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))
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
                                 task_id,
                                 form.description.data)
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
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))
    models = []
    return render_template('maintenance/models_list.html', 
                           version=version, models=models)    

@maintenance_blueprint.route('/category/edit/<category_id>', methods=['GET', 'POST'])
@login_required
def categ_edit(category_id):
    categ = Category.query.get(category_id)
    if categ is None:
        abort(404)
    version = categ.version
    if version.status in [3]:
        message = Markup(
            "<strong>Warning!</strong> Unable to edit category to committed version. ")
        flash(message, 'warning')
        return redirect(url_for('maintenance.categs_list', 
                                selected=version.name))
    form = EditCategoryForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                categ.name = form.name.data
                categ.description = form.description.data
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
    form.description.data = categ.description
    return render_template('maintenance/categ_edit.html', 
                           form=form,
                           categ=categ,
                           selected=version.name)

@maintenance_blueprint.route('/category/up/<category_id>', methods=['GET', 'POST'])
@login_required
def categ_up(category_id):
    categ = Category.query.get(category_id)
    if categ is None:
        abort(404)
    version = categ.version
    if version.status in [3]:
        message = Markup(
            "<strong>Warning!</strong> Unable to edit category to committed version. ")
        flash(message, 'warning')
        return redirect(url_for('maintenance.categs_list', 
                                selected=version.name))
    if categ.position == 0:
        message = Markup(
            "<strong>Warning!</strong> Category was not changed. ")
        flash(message, 'warning')
        return redirect(url_for('maintenance.categs_list', 
                                selected=version.name))
    try:
        categ_list = Category.list(categ.task, version.name)
        prev_categ = categ_list[categ.position - 1]
        categ.position -= 1
        prev_categ.position += 1
        db.session.commit()
        message = Markup("Saved successfully!")
        flash(message, 'success')
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        message = Markup(
            "<strong>Error!</strong> Unable to save this category. " + str(e))
        flash(message, 'danger')
    return redirect(url_for('maintenance.categs_list', 
                                selected=version.name))

@maintenance_blueprint.route('/category/down/<category_id>')
@login_required
def categ_down(category_id):
    categ = Category.query.get(category_id)
    if categ is None:
        abort(404)
    version = categ.version
    if version.status in [3]:
        message = Markup(
            "<strong>Warning!</strong> Unable to edit category to committed version. ")
        flash(message, 'warning')
        return redirect(url_for('maintenance.categs_list', 
                                selected=version.name))
    lc = Category.get_last(categ.version_id, categ.task)
    if categ.position == lc.position:
        message = Markup(
            "<strong>Warning!</strong> Category was not changed. ")
        flash(message, 'warning')
        return redirect(url_for('maintenance.categs_list', 
                                selected=version.name))
    try:
        categ_list = Category.list(categ.task, version.name)
        next_categ = categ_list[categ.position + 1]
        categ.position += 1
        next_categ.position -= 1
        db.session.commit()
        message = Markup("Saved successfully!")
        flash(message, 'success')
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        message = Markup(
            "<strong>Error!</strong> Unable to save this category. " + str(e))
        flash(message, 'danger')
    return redirect(url_for('maintenance.categs_list', 
                                selected=version.name))

@maintenance_blueprint.route('/category/del/<category_id>')
@login_required
def categ_del(category_id):
    categ = Category.query.get(category_id)
    if categ is None:
        abort(404)
    version = categ.version
    if version.status in [3]:
        message = Markup(
            "<strong>Warning!</strong> Unable to edit category to committed version. ")
        flash(message, 'warning')
        return redirect(url_for('maintenance.categs_list', 
                                selected=version.name))
    try:
        categ_list = Category.list(categ.task, version.name)
        upd = []
        for i in range(categ.position + 1, len(categ_list)):
            categ_list[i].position -= 1
            upd.append(categ_list[i])
        db.session.delete(categ)
        db.session.commit()
        message = Markup("Saved successfully!")
        flash(message, 'success')
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        message = Markup(
            "<strong>Error!</strong> Unable to delete this category. " + str(e))
        flash(message, 'danger')
    return redirect(url_for('maintenance.categs_list', 
                                selected=version.name))

@maintenance_blueprint.route('/category/help/<task_id>')
@login_required
def categ_help(task_id):
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.query.filter_by(name=selected).first()
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))
    categs = Category.list(task_id, version.name)
    helptext = [(c.name, c.description) for c in categs]
    return render_template('maintenance/help.html', 
                           helptext=helptext,
                           task_id=task_id,
                           version=version)

def render_diff(lstr):
    out = []
    for row in lstr:
        if row[0] == ' ':
            out.append((False, row[2:],
                        False, row[2:]))
        elif row[0] == '-':
            out.append((True, row[2:],
                        False, ''))
        elif row[0] == '+':
            out.append((False, '',
                        True, row[2:]))
        elif row[0] == '?':
            pass
            # out.append((True, row[2:],
            #             True, row[2:]))
    return out
                

@maintenance_blueprint.route('/category/helpdiff/<task_id>/<int:backsteps>')
@login_required
def help_diff(task_id, backsteps):
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.query.filter_by(name=selected).first()
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))
    current = version
    parent = version
    for cnt in range(backsteps):
        parent = current.parent()
        if parent is None:
            parent = current
            break
        else:
            current = parent
    categs_this = Category.list(task_id, version.name)
    helptext_this = dict([(c.name, 
                           (c.description or '').splitlines()) for c in categs_this])
    categs_parent = Category.list(task_id, parent.name)
    helptext_parent = dict([(c.name, 
                             (c.description or '').splitlines()) for c in categs_parent])
    diff = {}
    deltas = {}
    for categ_name in helptext_this.keys():
        if categ_name in helptext_parent:
            deltas[categ_name] = list(difflib.Differ().compare(
                                    helptext_this[categ_name],
                                    helptext_parent[categ_name]))
            diff[categ_name] = render_diff(deltas[categ_name])
        else:
            deltas[categ_name] = list(difflib.Differ().compare(
                                    helptext_this[categ_name],
                                    ''))
            diff[categ_name] = render_diff(deltas[categ_name])
    
    return render_template('maintenance/help_diff.html', 
                           diff=diff,
                           backsteps=backsteps,
                           this=version,
                           parent=parent,
                           task_id=task_id)