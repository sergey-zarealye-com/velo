# project/users/views.py

# IMPORTS
import logging
import os
from flask import (
    render_template,
    Blueprint,
    request,
    abort,
    send_from_directory,
    redirect,
    flash,
    session,
    url_for,
    Markup
)
from flask_login import login_required
from project import db

from project.models import DataItems, Deduplication, Version
from project.datasets.utils import fillup_tmp_table
from project.datasets.queries import get_labels_of_version
from .utils import process_response, get_task_result


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

    db_result = Deduplication.query.filter_by(task_uid=task_id)

    if not task_id or not db_result:
        abort(404)

    for idx in ids_to_remove:
        temporary_storage[task_id][idx]['removed'] = True

    db_result.result = temporary_storage[task_id]
    db.session.commit()

    return ('', 204)


@dedup_blueprint.route('/uploads/<path:filename>')
def download_file(filename):
    entry = DataItems.query.filter_by(id=filename).first()

    if not entry:
        abort(404)

    storage_path = entry.path
    path, file = os.path.split(storage_path)

    if path[0] == '/':
        path = path[1:]

    directory = os.path.join(os.getenv('STORAGE_DIR'), path)

    return send_from_directory(directory, file, as_attachment=True)


@dedup_blueprint.route('/task_confirmation/<task_id>/<selected>/<is_dedup>')
def task_confirmation(task_id, selected, is_dedup):
    is_dedup = bool(int(is_dedup))
    return render_template(
        'deduplication/taskConfirmed.html',
        task_id=task_id,
        selected=selected,
        is_dedup=is_dedup
    )


@dedup_blueprint.route('/checkbox/<task_id>/<selected_ds>', methods=['POST'])
def save_result(task_id, selected_ds):
    selected = request.form.getlist('rm_checkbox')

    task = Deduplication.query.filter_by(task_uid=task_id).first()
    if task is None:
        abort(404)

    version = Version.query.filter_by(name=selected_ds).first()
    label_ids = get_labels_of_version(version.id)

    dedup_result = task.result['deduplication']
    filenames_to_remove = [
        os.path.join(
            os.getenv("STORAGE_DIR"),
            DataItems.query.filter_by(id=dedup_result[int(i)]['image1']).first().path
        )
        for i in selected
    ]
    print('\tFilenames to remove:', filenames_to_remove)

    storage_dir = os.getenv('STORAGE_DIR')
    assert storage_dir

    logging.info('Removing from submit')
    for filename in filenames_to_remove:
        try:
            if filename[0] == '/':
                filename = filename[1:]
            filepath = os.path.join(storage_dir, filename)
            os.remove(filepath)
        except Exception as err:
            print(err)

    logging.info('Removing from temp storage')

    if task_id not in temporary_storage:
        temporary_storage[task_id] = task.result.get('deduplication')

    for item in filter(lambda x: x['removed'], temporary_storage[task_id]):
        file_id = item['image1']
        filename = DataItems.query.filter_by(id=file_id).first().path

        try:
            if filename[0] == '/':
                filename = filename[1:]
            filepath = os.path.join(storage_dir, filename)
            os.remove(filepath)
        except Exception as err:
            print(err)

    fillup_tmp_table(
        label_ids,
        selected_ds,
        os.path.join(os.getenv("STORAGE_DIR"), task_id),
        version,
        create_missing_categories=task.create_missing_categories,
        version_name=selected_ds,
        set_category=task.set_category
    )

    return redirect(f'/datasets/select/{selected_ds}')


@dedup_blueprint.route('/<task_id>/<selected_ds>', methods=['GET'])
@login_required
def show_dedup(task_id, selected_ds):
    task = Deduplication.query.filter_by(task_uid=task_id).first()
    if task is None:
        abort(404)

    if task.result is None:
        response = get_task_result(task.celery_task_id)

        if not response:
            statuses = task.stages_status
            return render_template('deduplication/taskPending.html', task_id=task.task_uid, statuses=statuses)

        task = process_response(response)

    # page_length = request.args.get("num_items")
    # page_num = request.args.get("page_num")

    dedup_result = task.result.get('deduplication')

    if not dedup_result:
        return render_template('deduplication/taskFinished.html', task_id=task.task_uid)

    if task_id not in temporary_storage:
        images = dedup_result
        temporary_storage[task_id] = images
    else:
        images = list(filter(lambda x: not x['removed'], temporary_storage[task_id]))

    return render_template(
        'deduplication/deduplication4.html',
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


@dedup_blueprint.route('/tasks', methods=['GET'])
@login_required
def show_task_list():
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.get_first()
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))

    tasks = Deduplication.query.all()

    return render_template(
        '/deduplication/tasks.html',
        selected_ds=version.name,
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


@dedup_blueprint.route('/delete_task/<task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    if 'selected_version' in session:
        version = Version.query.filter_by(name=session['selected_version']).first()
    else:
        version = Version.get_first()
    if version is None:
        message = Markup("There was no version found!")
        flash(message, 'warning')
        return redirect(url_for('datasets.index'))

    
