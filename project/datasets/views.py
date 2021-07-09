# project/users/views.py

# IMPORTS
import os
from flask import render_template, Blueprint, request, redirect, url_for
from flask import flash, Markup, abort, session
from sqlalchemy.exc import IntegrityError
from flask_login import current_user, login_required
from itsdangerous import URLSafeTimedSerializer
from threading import Thread
from flask_mail import Message
from datetime import datetime, timedelta

from project import app, db, mail
from project.models import User, Version, VersionChildren, Category
from .forms import EditVersionForm, ImportForm, CommitForm, MergeForm
import graphviz
from uuid import uuid4
import traceback

# CONFIG
TMPDIR = os.path.join('project', 'static', 'tmp')
datasets_blueprint = Blueprint('datasets', __name__, 
                               template_folder='templates',
                               url_prefix='/datasets')


# ROUTES
@datasets_blueprint.route('/select/<selected>')
@login_required
def select(selected):
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    session['selected_version'] = selected
    srcStr = Version.dot_str(selected)
    fname = str(current_user.id)
    my_graph = graphviz.Digraph(name="my_graph", engine='dot')
    my_graph.src = graphviz.Source(srcStr, filename=None, directory=None, 
                                   format='svg', engine='dot', encoding='utf-8')
    #TODO remove tmp files!
    my_graph.src.render(fname, TMPDIR, 
                        view=False)
    my_graph.src.render(fname, TMPDIR, 
                        format='cmapx', view=False)
    with open (os.path.join(TMPDIR, fname + '.cmapx'), "r") as mapfile:
        maptext=mapfile.readlines()
    maptext=' '.join(maptext)
    is_active = version.actions_dict()
    return render_template('datasets/index.html', 
                           impath=fname + '.svg',
                           maptext=maptext,
                           rnd=str(uuid4()),
                           version=version,
                           is_active=is_active)

@datasets_blueprint.route('/index')
@login_required
def index():
    if 'selected_version' in session:
        first_one = Version.query.filter_by(name=session['selected_version']).first()
    else:
        first_one = Version.get_first()
    if first_one is None:
        first_one = Version('Init', 'Auto-created empty dataset', current_user.id)
        db.session.add(first_one)
        db.session.commit()
    return redirect(url_for('datasets.select', selected=first_one.name))

@datasets_blueprint.route('/edit/<selected>', methods=['GET', 'POST'])
@login_required
def edit(selected):
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    if version.status == 3:
        abort(400)
    form = EditVersionForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                version.name = Version.safe_id(form.name.data)
                version.description = form.description.data
                db.session.commit()
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select', 
                                        selected=version.name))
            except IntegrityError:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong>! Version name should be unique.")
                flash(message, 'danger')
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to edit this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/edit.html', 
                           version=version, form=form)

@datasets_blueprint.route('/init', methods=['GET', 'POST'])
@login_required
def init():
    form = EditVersionForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                version = Version(form.name.data,
                                  form.description.data,
                                  current_user.id)
                db.session.add(version)
                db.session.commit()
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select', 
                                        selected=version.name))
            except IntegrityError:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong>! Version name should be unique.")
                flash(message, 'danger')
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to save this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/init.html', 
                           form=form)

@datasets_blueprint.route('/branch/<selected>', methods=['GET', 'POST'])
@login_required
def branch(selected):
    parent = Version.query.filter_by(name=selected).first()
    if parent is None:
        abort(404)
    if parent.status in [1, 2]:
        abort(400)
    form = EditVersionForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                version = Version(form.name.data,
                                  form.description.data,
                                  current_user.id)
                version.status = 2
                db.session.add(version)
                db.session.commit()
                vc = VersionChildren(version.id, parent.id)
                db.session.add(vc)
                db.session.commit()
                #Copy categories from parent version:
                #TODO inefficient, in case of error rollback not possible and new version is already created!
                for task in Category.TASKS():
                    categs = Category.list(task[0], parent.name)
                    for parent_categ in categs:
                        child_categ = Category(parent_categ.name,
                                               version.id, 
                                               task[0],
                                               position=parent_categ.position)
                        db.session.add(child_categ)
                db.session.commit()
                #TODO -- copy images from parent version (to join tbl)? Must be able to browse them in new branched version
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select', 
                                        selected=version.name))
            except IntegrityError:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong>! Version name should be unique.")
                flash(message, 'danger')
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to save this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/branch.html', 
                           form=form, selected=selected)

@datasets_blueprint.route('/import/<selected>', methods=['GET', 'POST'])
@login_required
def import2ds(selected):
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    if version.status == 3:
        abort(400)
    form = ImportForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            # change status to STAGE which means that version is not empty
            version.status = 2
            db.session.commit()
            #TODO implement actual images import. For your convenience:
            print('flocation', form.flocation.data)
            print('reason', form.reason.data)
            print('category_select', form.category_select.data)
            print('category', form.category.data)
            print('is_score_model', bool(form.is_score_model.data))
            print('score_model', form.score_model.data)
            print('is_dedup', bool(form.is_dedup.data))
            print('is_size_control', bool(form.is_size_control.data))
            print('min_size', form.min_size.data)
            print('is_stub_control', bool(form.is_stub_control.data))
            print('is_valid_control', bool(form.is_valid_control.data))
            print('is_resize', bool(form.is_resize.data))
            print('resize_w', form.resize_w.data)
            print('resize_h', form.resize_w.data)
            
            #TODO update categories for current version, based on import results
            return redirect(url_for('datasets.select', selected=version.name))
    return render_template('datasets/import.html', 
                           form=form, selected=selected, version=version)

@datasets_blueprint.route('/commit/<selected>', methods=['GET', 'POST'])
@login_required
def commit(selected):
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    if version.status in [1, 3]:
        abort(400)
    form = CommitForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                version.status = 3
                db.session.commit()
                #TODO freeze image_id's in joining table
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select', 
                                        selected=version.name))
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to commit this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/commit.html', 
                           form=form, selected=selected, version=version)

@datasets_blueprint.route('/merge/<selected>', methods=['GET', 'POST'])
@login_required
def merge(selected):
    child = Version.query.filter_by(name=selected).first()
    if child is None:
        abort(404)
    if child.status in [3]:
        abort(400)
    form = MergeForm(request.form)
    parents = Version.query.filter(Version.status == 3) \
                        .order_by(Version.created_at.desc())
    form.target_select.choices = [(t.name, t.name) 
                                  for t in parents
                                  if t.name != selected and 
                                      not t.is_connected(child)]
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                version = Version.query.filter_by(name=form.target_select.data).first()
                if version.status in [1, 2]:
                    abort(400)
                vc = VersionChildren(child.id, version.id)
                db.session.add(vc)
                db.session.commit()
                #TODO -- update categories for merged branch
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.merge_categs', 
                                        child=child.name,
                                        parent=version.name))
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to save this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/merge.html', 
                           form=form, selected=selected)

@datasets_blueprint.route('/merge_categs/<parent>/<child>', methods=['GET', 'POST'])
@login_required
def merge_categs(parent, child):
    child = Version.query.filter_by(name=child).first()
    if child is None:
        abort(404)
    parent = Version.query.filter_by(name=parent).first()
    if parent is None:
        abort(404)
    if child.status in [3]:
        abort(400)
    categs = {}
    for task in Category.TASKS():
        child_categs = Category.list(task[0], child.name)
        parent_categs = Category.list(task[0], parent.name)
        categs[task[0]] = {}
        categs[task[0]]['child'] = child_categs
        categs[task[0]]['parent'] = parent_categs
    if request.method == 'POST':
        merged_list = {}
        is_error = False
        for task in Category.TASKS():
            task_categs_seq = []
            for ch_c in categs[task[0]]['child']:
                try:
                    pos = int(request.values['categ_%d' % ch_c.id])
                    task_categs_seq.append((pos, ch_c))
                except:
                    pass
            for pa_c in categs[task[0]]['parent']:
                try:
                    pos = int(request.values['categ_%d' % pa_c.id])
                    task_categs_seq.append((pos, pa_c))
                except:
                    pass
            task_categs_seq.sort(key=lambda o: o[0])
            checking_validity_list = [o[0] for o in task_categs_seq]
            if list(range(len(checking_validity_list))) != checking_validity_list:
                message = Markup(
                    "<strong>" + task[1] + "</strong> Wrong positions sequence: " + str(checking_validity_list))
                flash(message, 'danger')
                is_error = True
            else:
                merged_list[task[0]] = task_categs_seq
        if not is_error:
            try:
                # Insert categories for merged branch
                for task in Category.TASKS():
                    for d_categ in Category.list(task[0], child.name):
                        db.session.delete(d_categ)
                    for t_categ in merged_list[task[0]]:
                        categ = Category(t_categ[1].name,
                                         child.id,
                                         task[0],
                                         t_categ[0])
                        db.session.add(categ)
                db.session.commit()
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select', 
                                        selected=child.name))
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to save this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/merge_categs.html', 
                           categs=categs, 
                           tasks=dict(Category.TASKS()),
                           child=child, parent=parent)
