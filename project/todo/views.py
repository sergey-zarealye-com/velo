# project/users/views.py

# IMPORTS
import re

from flask import render_template, Blueprint, request, redirect, url_for
from flask import flash, Markup, abort, session
from sqlalchemy.exc import IntegrityError
from flask_login import login_user, current_user, login_required, logout_user
from itsdangerous import URLSafeTimedSerializer
from threading import Thread
from flask_mail import Message
from datetime import datetime, timedelta

from project import app, db, mail
from project.models import User, Version, Category, ToDoItem, Moderation
from .utils import natural_sort

# CONFIG
from ..datasets.forms import ImportForm

todo_blueprint = Blueprint('todo', __name__,
                           template_folder='templates',
                           url_prefix='/todo')

# ROUTES
@todo_blueprint.route('/index')
@login_required
def index():
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.get_first()

    q = Moderation.query.distinct("src").all()
    for i, t in enumerate(q):
        title = t.src.split(sep='/')[-1]
        todo = ToDoItem.query.filter_by(title=title).first()
        if todo is None:
            todo = ToDoItem(
                file_path=t.src,
                title=title,
                description='Description',
                gt_category=t.general_category
            )
            db.session.add(todo)
    db.session.commit()

    todoitems = ToDoItem.fetch_for_user(current_user.id)

    return render_template('todo/index.html', todoitems=todoitems)


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
    rows_of_interesting = Moderation.query.filter_by(src=todo.file_path).all()
    images_paths = [row.file for row in rows_of_interesting]
    images_paths = [(images_path.split(sep='/')[-1], i) for i, images_path in enumerate(natural_sort(images_paths))]
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
    print(request.values)
    # TODO -- save everything
    todo.finished_at = datetime.now()
    db.session.commit()
    return redirect(url_for('todo.index'))
