# project/users/views.py

# IMPORTS
import json
import math
import ntpath
import os
from collections import Counter

from flask import render_template, Blueprint, redirect, url_for, flash
from flask import abort, session, send_from_directory
from flask_login import login_required
from markupsafe import Markup

from project import app, db
from project.datasets.queries import get_nodes_above
from project.images.queries import get_items_of_version, get_uncommited_items
from project.models import Version, Category

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
    uncommitted_items = get_uncommited_items(db.session, selected)

    # get vision classes
    classes_info = {cl.name: 0 for cl in Category.list(Category.TASKS()[0][0], version.name)}
    # count items per class in current ds
    cur_ds_info = dict(Counter(getattr(item, 'label') for item in version_items+uncommitted_items))
    # map vision classes with cur_ds_info
    for key, value in cur_ds_info.items():
        if key in classes_info:
            classes_info[key] = value

    cb_all_cl_filters = True
    # if "browse_filters" exists in session
    if "browse_filters" in session:
        version_items_filter = []
        cur_filters = {"uncommitted": False, "committed": False }
        # show only uncommitted items
        if "uncommitted" in session['browse_filters'] and session['browse_filters']["uncommitted"]:
            version_items_filter += uncommitted_items
            cur_filters["uncommitted"] = True
        if "committed" in session['browse_filters'] and session['browse_filters']["committed"]:
            version_items_filter += version_items
            cur_filters["committed"] = True
        # filter by class
        if "class_filter" in session['browse_filters']: # and len(session['browse_filters']["class_filter"]):
            version_items_filter = [item for item in version_items_filter if item.label in session['browse_filters']["class_filter"]]
            cur_filters["class_filter"] = session['browse_filters']["class_filter"]
            if len(classes_info) != len(cur_filters["class_filter"]):
                cb_all_cl_filters = False
    # prepare virgin filters settings
    else:
        version_items_filter = uncommitted_items + version_items
        cur_filters = {"uncommitted": True, "committed": True}



    return render_template('browse/item.html',
                           version=version,
                           version_items=version_items_filter[(page - 1) * items:(page) * items],
                           ds_length={
                               "all": len(version_items)+len(uncommitted_items),
                               "committed": len(version_items),
                               "uncommitted": len(uncommitted_items)
                           },
                           cb_all_cl_filters = cb_all_cl_filters,
                           classes_info=classes_info,
                           pages=int(math.ceil(len(version_items_filter) / int(items))),
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
