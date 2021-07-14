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
)
from flask_login import current_user, login_required
from project import app

from project.models import Deduplication, Version
from project.datasets.views import fillup_tmp_table, get_labels_of_version


# CONFIG
TMPDIR = os.path.join('project', 'static', 'tmp')
dedup_blueprint = Blueprint(
    'deduplication', __name__, 
    template_folder='templates',
    url_prefix='/dedup'
)


@dedup_blueprint.route('/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(os.environ.get('STORAGE_DIR'), filename, as_attachment=True)


@dedup_blueprint.route('/task_confirmation/<task_id>/<selected>')
def task_confirmation(task_id, selected):
    return render_template('datasets/taskConfirmed.html', task_id=task_id, selected=selected)


@dedup_blueprint.route('/checkbox/<task_id>/<selected_ds>', methods=['POST'])
def print_list(task_id, selected_ds):
    selected = request.form.getlist('test_checkbox')
    import pdb
    pdb.set_trace()
    task = Deduplication.query.filter_by(task_uid=task_id).first()
    if task is None:
        abort(404)

    version = Version.query.filter_by(name=selected_ds).first()
    label_ids = get_labels_of_version(version.id)

    dedup_result = task.result['deduplication']
    filenames_to_remove = [
        os.path.join(os.getenv("STORAGE_DIR"), dedup_result[int(i)][0]) for i in selected
    ]
    print('\tFilenames to remove:', filenames_to_remove)
    for filename in filenames_to_remove:
        try:
            os.remove(filename)
        except Exception as err:
            print(err)

    fillup_tmp_table(
        label_ids,
        selected_ds,
        os.path.join(os.getenv("STORAGE_DIR"), task_id),
        version
    )

    return redirect('/dataset/select', selected=selected_ds)


@dedup_blueprint.route('/<task_id>/<selected_ds>', methods=['GET'])
@login_required
def show_dedup(task_id, selected_ds):
    task = Deduplication.query.filter_by(task_uid=task_id).first()
    if task is None:
        abort(404)

    if task.result is None:
        statuses = task.stages_status
        return render_template('datasets/taskPending.html', task_id=task.task_uid, statuses=statuses)

    page_length = request.args.get("num_items")
    page_num = request.args.get("page_num")

    dedup_result = task.result['deduplication']
    images = [
        {
            'item_index': i,
            'image1': row[0],
            'image2': row[1],
            'similarity': row[2]
        }
        for i, row in enumerate(dedup_result)
    ]

    return render_template(
        'datasets/deduplication.html',
        images=images,
        task_id=task_id,
        selected_ds=selected_ds
    )
