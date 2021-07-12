# project/users/views.py

# IMPORTS
from flask import render_template, Blueprint, redirect, url_for
from flask import abort, session
from flask_login import login_required

from project.models import Version, VersionItems, DataItems

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
    image_ids = VersionItems.query.filter_by(version_id=8).with_entities(VersionItems.item_id)
    image_items = DataItems.query.filter(DataItems.id.in_(image_ids))
    return render_template('images/index.html', version=version, image_items=image_items)


if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("postgresql://velo:123@localhost:5432/velo")
    Session = sessionmaker(bind=engine)
    session = Session()

    image_ids = VersionItems.query.filter_by(version_id=8).with_entities(VersionItems.item_id)
    image_paths = DataItems.query.filter(DataItems.id.in_(image_ids))

    res = image_paths.all()
    print(res)
