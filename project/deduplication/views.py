# project/users/views.py

# IMPORTS
import os
from flask import (
    render_template,
    Blueprint,
    request,
    abort,
    send_from_directory,
    redirect,
    url_for,
    flash,
    Markup,
)
from flask_login import current_user, login_required

from project.models import Deduplication


# CONFIG
TMPDIR = os.path.join('project', 'static', 'tmp')
dedup_blueprint = Blueprint(
    'deduplication', __name__, 
    template_folder='templates',
    url_prefix='/dedup'
)


@dedup_blueprint.route('/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory('/storage1/mrowl/smoke', filename, as_attachment=True)


@dedup_blueprint.route('/task_confirmation/<task_id>/<selected>')
def task_confirmation(task_id, selected):
    return render_template('datasets/taskConfirmed.html', task_id=task_id, selected=selected)


@dedup_blueprint.route('/checkbox', methods=['POST'])
def print_list():
    selected = request.form.getlist('test_checkbox')
    print('\tSelected:', selected)
    print(request.form)
    return redirect('/datasets/select/new_dataset')


@dedup_blueprint.route('/<task_id>', methods=['GET'])
@login_required
def show_dedup(task_id):
    task = Deduplication.query.filter_by(task_uid=task_id).first()
    if task is None:
        abort(404)

    page_length = request.args.get("num_items")
    page_num = request.args.get("page_num")

    # check if there is directory with task_id
    full_path = '/storage1/mrowl/smoke/'
    if not os.path.isdir(full_path):
        print("Not found")
        return abort(404)

    return render_template(
        'datasets/deduplication.html',
        images=[
            {
                'item_index': i,
                'image1': filename,
                'image2': filename,
                'similarity': 0.89
            }
            for i, filename in enumerate(os.listdir(full_path)[:10])
        ]
    )
