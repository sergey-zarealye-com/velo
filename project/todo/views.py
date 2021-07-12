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
from project.models import User, Version, Category, ToDoItem


# CONFIG
todo_blueprint = Blueprint('todo', __name__, 
                           template_folder='templates',
                           url_prefix='/todo')

######### TODO TEMPORARY
def init_mockup_data():
    texts = ['a', 'b', 'c', 'd']
    for i, t in enumerate(texts):
        todo = ToDoItem.query.filter_by(title=t).first()
        if todo is None:
            todo = ToDoItem(t, t, t, 'PORNO')
            db.session.add(todo)
    db.session.commit()
######### REMOVE ^^ 

# ROUTES
@todo_blueprint.route('/index')
@login_required
def index():
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.query.filter_by(name=selected).first()
    #TODO REMOVE THIS:
    init_mockup_data()
    ###################
    
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
        version = Version.query.filter_by(name=selected).first()
    todo.started_at = datetime.now()
    todo.user_id = current_user.id
    todo.version_id = version.id
    db.session.commit()
    ##TODO -- после того, как закрепили задание за юзером, запустить раскадровку и speech to text
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
        version = Version.query.filter_by(name=selected).first()
    categs = {}
    for task in Category.TASKS():
        categs[task[0]] = Category.list(task[0], version.name)
    #TODO -- сюда подставить реальные кадры
    RANDOM_PIC = "https://source.unsplash.com/random/200x200?sig=%d"
    frames = [(RANDOM_PIC % i, i) for i in range(25)]
    ###########
    return render_template('todo/item.html', todo=todo, 
                           categs=categs,
                           frames=frames,
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
    #TODO -- save everything
    todo.finished_at = datetime.now()
    db.session.commit()
    return redirect(url_for('todo.index'))