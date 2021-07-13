# project/users/views.py

# IMPORTS
import os
from flask import render_template, Blueprint, request, redirect, url_for, flash, Markup, abort
from sqlalchemy.exc import IntegrityError
from flask_login import current_user, login_required
from itsdangerous import URLSafeTimedSerializer
from threading import Thread
from flask_mail import Message
from datetime import datetime, timedelta

from project import app, db, mail
from project.models import User, Version, VersionChildren
from .forms import EditVersionForm, ImportForm, CommitForm, MergeForm
import graphviz
from uuid import uuid4
import traceback

from multiprocessing import Process, Queue
from .rabbitmq_connector import send_message, get_message
import json
import uuid


# Processes for communication module
sending_queue: Queue = Queue()
sending_process = Process(
    target=send_message,
    args=('deduplication_1', sending_queue)
)
sending_process.start()

pulling_queue: Queue = Queue()
pulling_process = Process(
    target=get_message,
    args=('deduplication_result_1', pulling_queue)
)
pulling_process.start()

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
    return render_template('datasets/list.html', 
                           impath=fname + '.svg',
                           maptext=maptext,
                           rnd=str(uuid4()),
                           version=version,
                           is_active=is_active)

@datasets_blueprint.route('/list')
@login_required
def list():
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
                db.session.add(version)
                db.session.commit()
                vc = VersionChildren(version.id, parent.id)
                db.session.add(vc)
                db.session.commit()
                #TODO -- copy categories for new branch
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

            task_id = str(uuid.uuid4())

            sending_queue.put(
                (task_id, json.dumps({
                    'id': task_id,
                    'directory': form.flocation.data,
                    'is_size_control': form.is_size_control.data,
                    'min_size': form.min_size.data,
                    'is_resize': bool(form.is_resize.data),
                    'dst_size': (int(form.resize_h.data), int(form.resize_w.data)),
                    'deduplication': bool(form.is_dedup.data),
                }))
            )
            
            #TODO update categories for current version, based on import results
            # return redirect(url_for('datasets.select', selected=version.name))
            return redirect(url_for('deduplication.task_confirmation', task_id=task_id, selected=version.name))
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
    parent = Version.query.filter_by(name=selected).first()
    if parent is None:
        abort(404)
    if parent.status in [1, 2]:
        abort(400)
    form = MergeForm(request.form)
    targets = Version.query.filter(Version.status < 3)
    form.target_select.choices = [(t.name, t.name) 
                                  for t in targets
                                  if t.name != selected]
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                version = Version.query.filter_by(name=form.target_select.data).first()
                if version.status == 3:
                    abort(400)
                vc = VersionChildren(version.id, parent.id)
                db.session.add(vc)
                db.session.commit()
                #TODO -- update categories for merged branch
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select', 
                                        selected=version.name))
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to save this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/merge.html', 
                           form=form, selected=selected)
