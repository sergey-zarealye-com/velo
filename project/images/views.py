# project/users/views.py

# IMPORTS
from flask import render_template, Blueprint, redirect, url_for
from flask import abort, session
from flask_login import login_required

from project import db
from project.datasets.queries import get_nodes_above
from project.images.queries import get_items_of_version
from project.models import Version, VersionItems, DataItems, Category

# CONFIG
images_blueprint = Blueprint('images', __name__,
                             template_folder='templates',
                             url_prefix='/images')


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


@images_blueprint.route('/browse/<selected>')
@login_required
def browse(selected):
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    nodes_of_version = get_nodes_above(db.session, version.id)
    version_items = get_items_of_version(db.session, nodes_of_version)
    return render_template('images/index.html', version=version, version_items=version_items)


if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("postgresql://velo:123@localhost:5432/velo")
    Session = sessionmaker(bind=engine)
    session = Session()

    # image_ids = VersionItems.query.filter_by(version_id=1).with_entities(VersionItems.item_id, VersionItems.category_id).all()
    # image_paths = DataItems.query.filter(DataItems.id.in_(image_ids)).join(Category, Category.c.id == image_ids.category_id)

    # node_items = VersionItems.query.filter_by(version_id=1)
    """
    category_id
    item_id
    """
    q = session.query(VersionItems, DataItems, Category) \
        .filter(VersionItems.version_id == 1) \
        .join(DataItems) \
        .filter(Category.id == VersionItems.category_id)

    for item in q.all():
        print(item)
