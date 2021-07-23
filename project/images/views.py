# project/users/views.py

# IMPORTS
import json
import math
import ntpath
from collections import Counter

from flask import render_template, Blueprint, redirect, url_for, flash
from flask import abort, session, send_from_directory
from flask_login import login_required
from markupsafe import Markup

from project import app, db
from project.datasets.queries import get_nodes_above
from project.images.queries import get_items_of_version, get_uncommited_items
from project.models import Version
import os

# CONFIG
images_blueprint = Blueprint('images', __name__,
                             template_folder='templates',
                             url_prefix='/images')


# TODO: сделать логгер, вынести в него все принты

# ROUTES
@images_blueprint.route('/index')
@login_required
def index():
    if 'selected_version' in session:
        first_one = Version.query.filter_by(name=session['selected_version']).first()
    else:
        first_one = Version.get_first()
    if first_one is None:
        abort(404)
    return redirect(url_for('images.browse', selected=first_one.name))


@images_blueprint.route('/uploads/<path:filename>')
def download_file(filename):
    # todo: исправить костыль
    filename = filename.replace('\\', '/')
    head, tail = ntpath.split(filename)
    if not os.path.exists(head):
        head = "/" + head
    return send_from_directory(head, tail, as_attachment=True)


@images_blueprint.route('/browse/<selected>')
@images_blueprint.route('/browse/<selected>&page=<page>&items=<items>')
@images_blueprint.route('/browse/<selected>&page=<page>&items=<items>&filters=<filters>')
@login_required
def browse(selected, page=1, items=50, filters=None):
    app.logger.info(f"Filters: {filters}")
    try:
        items = int(items)
        page = int(page)
        if filters is not None:
            filters = json.loads(filters)
            session['browse_filters'] = filters
    except Exception as e:
        app.logger.error(e)
        abort(404)
    msg = f"Selected node: {selected}. Page: {page}\nItems: {items}\t{(page - 1) * items}:{(page) * items}]\nFilters: {filters}"
    app.logger.info(msg)
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.query.filter_by(name=selected).first()
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))
    nodes_of_version = get_nodes_above(db.session, version.id)
    version_items = get_items_of_version(db.session, nodes_of_version)
    # TODO: отобразить на фронте
    uncommited_items = get_uncommited_items(db.session, selected)
    classes_info = dict(Counter(getattr(item, 'label') for item in version_items))
    if "browse_filters" in session:
        version_items_filtr = [item for item in version_items if item.label in session['browse_filters']]
        cur_filters = session['browse_filters']
    else:
        cur_filters = None
        version_items_filtr = version_items

    return render_template('browse/item.html',
                           version=version,
                           version_items=version_items_filtr[(page - 1) * items:(page) * items],
                           ds_length=len(version_items),
                           classes_info=classes_info,
                           pages=int(math.ceil(len(version_items_filtr) / int(items))),
                           page=page,
                           items=items,
                           filters=cur_filters)


if __name__ == '__main__':
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("postgresql://velo:123@localhost:5432/velo")
    Session = sessionmaker(bind=engine)
    session = Session()

    pass
