# project/users/views.py

# IMPORTS
import os.path
import re
import time

from pathlib import Path
import logging
import pandas as pd
from flask import render_template, Blueprint, request, redirect, url_for
from flask import flash, Markup, abort, session
from sqlalchemy.exc import IntegrityError
from flask_login import login_user, current_user, login_required, logout_user
from itsdangerous import URLSafeTimedSerializer
from threading import Thread
from flask_mail import Message
from datetime import datetime, timedelta

from project import app, db, mail
from project.models import User, Version, Category, ToDoItem, Moderation, DataItems, TmpTable, VersionItems
from .utils import natural_sort
from .forms import NewBatchForm

# CONFIG
from ..datasets.forms import ImportForm
from ..datasets.queries import get_labels_of_version
from ..datasets.utils import create_video_task, pulling_queue

todo_blueprint = Blueprint('todo', __name__,
                           template_folder='templates',
                           url_prefix='/todo')

log = logging.getLogger(__name__)
ABS_PATH = Path.absolute(Path('project')).joinpath('static', 'images', 'tmp')


# ROUTES
@todo_blueprint.route('/index')
@login_required
def index():
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.get_first()
    # ToDo подумать как сделать лаконичнее (потом)
    while not pulling_queue.empty():
        data = pulling_queue.get()
        path = ABS_PATH.joinpath(data['task_id'], 'thumbs')
        file_list = os.listdir(path)
        objects = []
        for file in file_list:
            sample_path = os.path.join(path, file)
            item2moderate = Moderation(src=str(path),
                                       file=sample_path,
                                       src_media_type="VIDEO", #ToDO расхардкодить
                                       category=data["cat"],
                                       description=data["description"],
                                       title=data["title"],
                                       id=data["video_id"])
            objects.append(item2moderate)
        try:
            db.session.bulk_save_objects(objects, return_defaults=True)
            db.session.commit()
        except Exception as ex:
            log.error(ex)
            db.session.rollback()

    print("В def index() ", id(pulling_queue))
    q = Moderation.query.distinct("id").all()
    for i, t in enumerate(q):
        todo = ToDoItem.query.filter_by(id=t.id).first()
        if todo is None:
            todo = ToDoItem(
                file_path=t.src,
                title=t.title,
                description=t.description,
                gt_category=t.category,
                id=t.id
            )
            db.session.add(todo)
    db.session.commit()

    todoitems = ToDoItem.fetch_for_user(current_user.id)
    return render_template('todo/index.html', todoitems=todoitems, version=version)


@todo_blueprint.route('/take/<item_id>', methods=['POST'])
@login_required
def take(item_id):
    todo = ToDoItem.query.get(item_id)
    if todo is None:
        abort(404)
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.get_first()
    todo.started_at = datetime.now()
    todo.user_id = current_user.id
    todo.version_id = version.id
    db.session.commit()

    return redirect(url_for('todo.item', item_id=todo.id))


@todo_blueprint.route('/item/<item_id>')
@login_required
def item(item_id):
    todo = ToDoItem.query.get(item_id)
    if todo is None:
        abort(404)
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.get_first()
    categs = {}
    for task in Category.TASKS():
        categs[task[0]] = Category.list(task[0], version.name)
    rows_of_interesting = Moderation.query.filter_by(id=todo.id).all()
    images_paths = [Path(row.file) for row in rows_of_interesting]
    images_paths = [(images_path.anchor.join(images_path.parts[-3:]), i) for i, images_path in enumerate(natural_sort(images_paths))]
    return render_template('todo/item.html', todo=todo,
                           categs=categs,
                           frames=images_paths,
                           version=version,
                           tasks=dict(Category.TASKS()))


@todo_blueprint.route('/moderate/<item_id>', methods=['POST'])
@login_required
def moderate(item_id):
    todo = ToDoItem.query.get(item_id)
    if todo is None:
        abort(404)
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        abort(400)
    req_values = request.values
    print(req_values)
    film_id = ToDoItem.query.filter_by(id=item_id).first().id
    rows_of_interesting = Moderation.query.filter_by(id=film_id).all()
    images_paths = [row.file for row in rows_of_interesting]
    images_paths = [images_path for i, images_path in enumerate(natural_sort(images_paths))]
    objects = []
    items = TmpTable.query.distinct('item_id').all()
    if items:
        max_id = max([item.id for item in items]) + 1
    else:
        max_id = 0
    for images_path, value in zip(images_paths, req_values.values()):
        if value == '-1':
            Moderation.query.filter_by(file=images_path).delete()
            os.remove(images_path)
        else:
            # ToDo реализовать сохранение в датасет
            item_to_save = TmpTable(
                item_id=max_id,
                node_name=version.name,
                category_id=Category.query.filter_by(version_id=version.id)
            )
    todo.finished_at = datetime.now()
    db.session.commit()
    ToDoItem.query.filter_by(id=film_id).delete()
    return {"status": True}
    # return redirect(url_for('todo.index'))


@todo_blueprint.route('/new_batch', methods=['GET', 'POST'])
@login_required
def new_batch():
    form = NewBatchForm(request.form)
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        abort(400)
    label_ids = get_labels_of_version(version.id)

    if request.method == 'POST':
        if form.validate_on_submit():
            user_id = current_user.id
            created_at = datetime.now()
            # TODO -- add queue to download and preprocess videos and create todo items
            with open(form.src.data) as f:
                data = pd.read_csv(f)

            paths, cats, titles, descriptions = [data.video_adress.values,
                                                 data.gt_category.values,
                                                 data.title.values,
                                                 data.description.values]
            items = ToDoItem.query.distinct('id').all()
            if items:
                max_id = max([item.id for item in items])
            else:
                max_id = 0
            for i, (path, cat, title, description) in enumerate(zip(paths, cats, titles, descriptions), start=max_id+1):
                # ToDo написать по человечески
                create_video_task(path, version.id, cat, description, title, i)
            return redirect(url_for('todo.index'))
    return render_template('todo/new_batch.html',
                           form=form)
