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
from project.models import User


# CONFIG
images_blueprint = Blueprint('images', __name__, 
                             template_folder='templates',
                             url_prefix='/images')


# ROUTES
@images_blueprint.route('/list')
def list():
    return render_template('images/list.html')
