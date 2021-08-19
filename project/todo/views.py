# project/users/views.py

# IMPORTS
import json
import os.path
import shutil
import uuid

from pathlib import Path
import logging
import pandas as pd
import transliterate
from celery.result import AsyncResult
from celery.worker.control import revoke
from flask import render_template, Blueprint, request, redirect, url_for
from flask import flash, Markup, abort, session
from flask_login import current_user, login_required
from datetime import datetime

from project import db
from project.models import Version, Category, ToDoItem, Moderation, CeleryTask
from .utils import natural_sort
from .forms import NewBatchForm

# CONFIG
from ..datasets.queries import get_labels_of_version
from project.datasets.utils import fillup_tmp_table
from project.todo.utils import create_video_task
from project.celery.tasks import app

todo_blueprint = Blueprint('todo', __name__,
                           template_folder='templates',
                           url_prefix='/todo')

log = logging.getLogger(__name__)
ABS_PATH = Path(os.getenv('MODERATION_STORAGE_DIR'))
TMP_PATH = ABS_PATH.joinpath('tmp')

SAVE_PATH = ABS_PATH.joinpath('save_dir')
for path in (SAVE_PATH, TMP_PATH):
    if not path.exists():
        path.mkdir()


# ROUTES
@todo_blueprint.route('/index')
@login_required
def index():
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.get_first()
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))

    # ToDo написать обработку получения результатов для отображения
    tasks = CeleryTask.query.filter_by(for_checkout=False).all()
    for task in tasks:
        task_id = task.cv_task_id
        video_uuid = task.video_uuid
        task_res = AsyncResult(task_id, app=app)
        task_status = task_res.state
        todo = ToDoItem.query.filter_by(video_uuid=video_uuid).first()
        todo.cv_status = task_status
        if task_status == "SUCCESS":
            CeleryTask.query.filter_by(cv_task_id=task_id).delete()
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
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))
    todo.started_at = datetime.now()
    todo.user_id = current_user.id
    todo.version_id = version.id
    path = TMP_PATH.joinpath(todo.file_path, 'thumbs')
    file_list = os.listdir(path)
    objects = []
    for file in file_list:
        sample_path = os.path.join(path, file)
        item2moderate = Moderation(src=str(path),
                                   file=sample_path,
                                   src_media_type="VIDEO",  # ToDO расхардкодить
                                   category=todo.gt_category,
                                   description=todo.description,
                                   title=todo.title,
                                   id=todo.id)
        objects.append(item2moderate)
    try:
        db.session.bulk_save_objects(objects, return_defaults=True)
        db.session.commit()
    except Exception as ex:
        log.error(ex)
        db.session.rollback()
    return redirect(url_for('todo.item', item_id=todo.id))


@todo_blueprint.route('/delete/<item_id>', methods=['POST'])
@login_required
def delete(item_id):
    todo = ToDoItem.query.get(item_id)
    if todo is None:
        abort(404)
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.get_first()
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))
    cv_task = CeleryTask.query.filter_by(video_uuid=todo.video_uuid).first()
    if cv_task is not None:
        cv_task_id = cv_task.cv_task_id
        app.control.revoke(task_id=cv_task_id, terminate=True)
    shutil.rmtree(todo.file_path, ignore_errors=True)
    CeleryTask.query.filter_by(video_uuid=todo.video_uuid).delete()
    ToDoItem.query.filter_by(id=item_id).delete()
    db.session.commit()
    return redirect(url_for('todo.index'))


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
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))
    categs = {}
    for task in Category.TASKS():
        categs[task[0]] = Category.list(task[0], version.name)
    rows_of_interesting = Moderation.query.filter_by(id=todo.id).all()
    images_paths = [Path(row.file) for row in rows_of_interesting]
    images_paths = [(images_path, i) for i, images_path in enumerate(natural_sort(images_paths))]
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
    req_values = json.loads(list(request.form)[0])
    print(req_values)
    film_id = ToDoItem.query.filter_by(id=item_id).first().id
    rows_of_interesting = Moderation.query.filter_by(id=film_id).all()
    images_paths = [row.file for row in rows_of_interesting]
    images_paths = [images_path for i, images_path in enumerate(natural_sort(images_paths))]
    for k, v in req_values.items():
        images_path = images_paths[int(v['ver'])]
        category = Category.query.filter_by(id=int(v['cl'])).first().name
        if not os.path.exists(os.path.join(SAVE_PATH, category)):
            os.mkdir(os.path.join(SAVE_PATH, category))
        shutil.move(images_path, os.path.join(SAVE_PATH, category,
                                              transliterate.translit(f"{str(uuid.uuid4())}.jpg", 'ru', reversed=True)))
    Moderation.query.filter_by(id=film_id).delete()
    fillup_tmp_table(get_labels_of_version(version.id), version.name, str(SAVE_PATH), version, priority=1)
    folder = Path(images_paths[0]).parent.parent
    shutil.rmtree(folder, ignore_errors=True)
    todo.finished_at = datetime.now()
    db.session.commit()
    return f"status: {True}"


@todo_blueprint.route('/view_error/<task_id>', methods=['POST', 'GET'])
@login_required
def view_error(task_id):
    todo = ToDoItem.query.filter_by(video_uuid=task_id).first()
    task = CeleryTask.query.filter_by(video_uuid=todo.video_uuid).first()
    task_result = AsyncResult(task.cv_task_id, app=app)
    task_message = task_result.info
    traceback_text = [task_message]
    return render_template('todo/help.html', helptext=traceback_text)


@todo_blueprint.route('/new_batch', methods=['GET', 'POST'])
@login_required
def new_batch():
    form = NewBatchForm(request.form)
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        abort(400)

    if request.method == 'POST':
        if form.validate_on_submit():
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
            for i, (path, cat, title, description) in enumerate(zip(paths, cats, titles, descriptions),
                                                                start=max_id + 1):
                task_uuid = str(uuid.uuid4())
                task_meta = create_video_task(task_uuid, path, version.id, cat, description, title, i)
                if task_meta is not None:
                    task = CeleryTask(
                        cv_task_id=task_meta.task_id,
                        video_uuid=task_uuid
                    )
                    db.session.add(task)
                    todo = ToDoItem(
                        file_path=os.path.join(os.getenv("MODERATION_STORAGE_DIR"), 'tmp', task_uuid),
                        title=title,
                        description=description,
                        gt_category=cat,
                        id=i,
                        video_uuid=task_uuid
                    )
                    db.session.add(todo)
            db.session.commit()

            return redirect(url_for('todo.index'))
    return render_template('todo/new_batch.html',
                           form=form)
