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
from project.models import User, Version
import graphviz
from uuid import uuid4

# CONFIG
TMPDIR = os.path.join('project', 'static', 'tmp')
datasets_blueprint = Blueprint('datasets', __name__, 
                               template_folder='templates',
                               url_prefix='/datasets')


# ROUTES
@datasets_blueprint.route('/select/<selected>')
@login_required
def select(selected):
    srcStr = Version.dot_str(selected)
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
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