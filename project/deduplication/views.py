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
    flash
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
temporary_storage = {}


@dedup_blueprint.route('/rm', methods=['POST'])
def temporary_remove():
    content = request.get_json()
    ids_to_remove = content.get('checkboxes', [])
    task_id = content.get('task_id')

    if not task_id:
        abort(404)

    for idx in ids_to_remove:
        temporary_storage[task_id][idx]['removed'] = True

    return ('', 204)


@dedup_blueprint.route('/uploads/<path:filename>')
def download_file(filename):
    return send_from_directory(os.environ.get('STORAGE_DIR'), filename, as_attachment=True)


@dedup_blueprint.route('/task_confirmation/<task_id>/<selected>/<is_dedup>')
def task_confirmation(task_id, selected, is_dedup):
    is_dedup = bool(int(is_dedup))
    return render_template(
        'datasets/taskConfirmed.html',
        task_id=task_id,
        selected=selected,
        is_dedup=is_dedup
    )


@dedup_blueprint.route('/checkbox/<task_id>/<selected_ds>', methods=['POST'])
def save_result(task_id, selected_ds):
    selected = request.form.getlist('test_checkbox')

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

    import pdb
    pdb.set_trace()
    return redirect(f'/dataset/select/{selected_ds}')


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

    dedup_result = task.result.get('deduplication')

    if not dedup_result:
        return render_template('datasets/taskFinished.html', task_id=task.task_uid)

    if not task_id in temporary_storage:
        images = [
            {
                'item_index': i,
                'image1': row[0],
                'image2': row[1],
                'similarity': row[2],
                'removed': False
            }
            for i, row in enumerate(dedup_result)
        ]
        temporary_storage[task_id] = images
    else:
        images = list(filter(lambda x: not x['removed'], temporary_storage[task_id]))

    return render_template(
        'datasets/deduplication4.html',
        images=images,
        task_id=task_id,
        selected_ds=selected_ds,
        count_items=len(images)
    )


@dedup_blueprint.route('/take/<task_id>/<selected_ds>', methods=['GET'])
@login_required
def take_task(task_id, selected_ds):
    print('Got task', task_id, selected_ds)

    task_entry = Deduplication.query.filter_by(task_uid=task_id)

    if not task_entry:
        abort(404)

    return show_dedup(task_id, selected_ds)


@dedup_blueprint.route('/tasks/<selected_ds>', methods=['GET'])
@login_required
def show_task_list(selected_ds):
    version = Version.query.filter_by(name=selected_ds).first()
    tasks = Deduplication.query.all()

    return render_template(
        '/deduplication/tasks.html',
        selected_ds=selected_ds,
        version=version,
        tasks=[
            {
                'status': task.task_status,
                'created_at': task.created_at,
                'started_at': task.started_at,
                'task_id': task.task_uid,
                'can_take': bool(task.result)
            }
            for task in tasks
        ]
    )
