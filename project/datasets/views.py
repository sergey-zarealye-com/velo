import logging
import os
from typing import List, Dict, Set, Tuple

from flask import render_template, Blueprint, request, redirect, url_for
from flask import flash, Markup, abort, session
from sqlalchemy.exc import IntegrityError
from flask_login import current_user, login_required

from project import db, app
from project.images.queries import get_uncommited_items
from project.models import Version, VersionChildren, DataItems, TmpTable, Category, Changes
from .forms import EditVersionForm, ImportForm, CommitForm, MergeForm, SplitForm
from project.models import Model
import graphviz
from uuid import uuid4
import traceback
from distutils.dir_util import copy_tree
import sys
import shutil

from project.celery.tasks import upload_files_to_storage

from multiprocessing import Process, Queue
from .rabbitmq_connector import send_message
import uuid
from project.datasets.queries import get_labels_of_version, get_nodes_above, get_items_of_nodes, prepare_to_commit, \
    get_items_of_nodes_with_label, update_tmp
from project.deduplication.utils import create_image_processing_task
from project.datasets.utils import split_data_items
from project.datasets.utils import TaskManager

log = logging.getLogger(__name__)

# CONFIG
TMPDIR = os.path.join('project', 'static', 'tmp')
datasets_blueprint = Blueprint('datasets', __name__,
                               template_folder='templates',
                               url_prefix='/datasets')

# TODO: вынести процессы в какой нибудь init файл

# Processes for communication module
commit_queue: Queue = Queue()
commit_process = Process(
    target=send_message,
    args=(commit_queue,),
    daemon=True
)
commit_process.start()

task_queue: Queue = Queue()
task_manager = TaskManager(task_queue)
task_proc = Process(
    target=task_manager.run,
    daemon=True
)
task_proc.start()

shortlife_processes: List[Process] = []


def copy_directory(
        src_dir: str,
        dst_path: str,
        task_id: str,
        is_size_control: bool,
        min_size: Tuple[int, int],
        is_resize: bool,
        dst_size: Tuple[int, int],
        is_dedup: bool,
        label_ds: Dict[str, int],
        selected_ds: str,
        create_missing_cats: bool,
        is_scoring: bool,
        scoring_model: str
):
    logging.info("Start copying data...")
    sys.stdout.flush()

    os.mkdir(dst_path)
    copy_tree(src_dir, dst_path)

    logging.info("Finish copying data")
    logging.info("Sending task to queue...")
    sys.stdout.flush()

    message = {
        'id': task_id,
        'directory': task_id,
        'is_size_control': is_size_control,
        'min_size': min_size,
        'is_resize': bool(is_resize),
        'dst_size': tuple(dst_size),
        'deduplication': bool(is_dedup),
        'label_ds': label_ds,
        'selected_ds': selected_ds,
        'is_scoring': is_scoring,
        'scoring_model': scoring_model
    }
    celery_task, celery_task_id = create_image_processing_task(message)
    print('celery task_id:', celery_task_id)
    task_queue.put(celery_task)

    commit_queue.put((task_id, celery_task_id, create_missing_cats))
    log.info("Processing entry created")

    logging.info(f"Sended task with id {task_id}")
    sys.stdout.flush()


def send_merge_control_request(filepaths: List[str]):
    storage_dir = os.getenv('STORAGE_DIR')
    assert storage_dir, "STORAGE_DIR can't be empty"

    task_id = str(uuid.uuid4())
    while task_id in os.listdir(storage_dir):
        task_id = str(uuid.uuid4())

    task_dir = os.path.join(storage_dir, task_id)
    os.mkdir(task_dir)

    names_mapping: Dict[str, str] = {}
    unique_names: Set[str] = set()
    while len(unique_names) < len(filepaths):
        unique_names.add(str(uuid.uuid4()))
    unique_names = list(unique_names)  # type: ignore

    # copy files to storage
    for src_path, dst_filename in zip(filepaths, unique_names):
        dst_path = os.path.join(task_dir, dst_filename)
        shutil.copy(src_path, dst_path)
        names_mapping[dst_path] = src_path

    message = {
        'id': task_id,
        'type': 'merge_control',
        'directory': task_dir,
        'merge_check': True,
        'names_mapping': names_mapping
    }
    create_image_processing_task(message)


# ROUTES
@datasets_blueprint.route('/select/<selected>')
@login_required
def select(selected):
    version = Version.query.filter_by(name=selected).first()

    if version is None:
        abort(404)

    if session.get('selected_version') != selected:
        session.pop('browse_filters', None)

    session['selected_version'] = selected
    srcStr = Version.dot_str(selected)
    fname = str(current_user.id)
    my_graph = graphviz.Digraph(name="my_graph", engine='dot')
    my_graph.src = graphviz.Source(srcStr, filename=None, directory=None,
                                   format='svg', engine='dot', encoding='utf-8')
    # TODO remove tmp files!
    my_graph.src.render(fname, TMPDIR,
                        view=False)
    my_graph.src.render(fname, TMPDIR,
                        format='cmapx', view=False)
    with open(os.path.join(TMPDIR, fname + '.cmapx'), "r") as mapfile:
        maptext = mapfile.readlines()
    maptext = ' '.join(maptext)
    is_active = version.actions_dict()
    return render_template('datasets/index.html',
                           impath=fname + '.svg',
                           maptext=maptext,
                           rnd=str(uuid4()),
                           version=version,
                           is_active=is_active)


@datasets_blueprint.route('/index')
@login_required
def index():
    if 'selected_version' in session:
        first_one = Version.query.filter_by(name=session['selected_version']).first()
    else:
        first_one = Version.get_first()
    if first_one is None:
        try:
            first_one = Version('Init', 'Auto-created empty dataset', current_user.id)
            db.session.add(first_one)
            db.session.commit()
        except Exception as ex:
            log.error(ex)
            db.session.rollback()
    return redirect(url_for('datasets.select', selected=first_one.name))


@datasets_blueprint.route('/edit/<selected>', methods=['GET', 'POST'])
@login_required
def edit(selected):
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    if version.status == 3:
        abort(400)
    form = EditVersionForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                version.name = Version.safe_id(form.name.data)
                version.description = form.description.data
                db.session.commit()
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select',
                                        selected=version.name))
            except IntegrityError:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong>! Version name should be unique.")
                flash(message, 'danger')
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to edit this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/edit.html',
                           version=version, form=form)


@datasets_blueprint.route('/init', methods=['GET', 'POST'])
@login_required
def init():
    form = EditVersionForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                version = Version(form.name.data,
                                  form.description.data,
                                  current_user.id)
                db.session.add(version)
                db.session.commit()
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select',
                                        selected=version.name))
            except IntegrityError:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong>! Version name should be unique.")
                flash(message, 'danger')
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to save this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/init.html',
                           form=form)


@datasets_blueprint.route('/branch/<selected>', methods=['GET', 'POST'])
@login_required
def branch(selected):
    parent = Version.query.filter_by(name=selected).first()
    if parent is None:
        abort(404)
    if parent.status in [1, 2]:
        abort(400)
    form = EditVersionForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                version = Version(form.name.data,
                                  form.description.data,
                                  current_user.id)
                version.status = 2
                db.session.add(version)
                db.session.commit()
                vc = VersionChildren(version.id, parent.id)
                db.session.add(vc)
                db.session.commit()
                # Copy categories from parent version:
                # TODO inefficient, in case of error rollback not possible and new version is already created!
                for task in Category.TASKS():
                    categs = Category.list(task[0], parent.name)
                    for parent_categ in categs:
                        child_categ = Category(
                            parent_categ.name,
                            version.id,
                            task[0],
                            parent_categ.description,
                            position=parent_categ.position
                        )
                        db.session.add(child_categ)
                db.session.commit()
                # TODO -- copy images from parent version (to join tbl)? Must be able to browse them in new branched version
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select',
                                        selected=version.name))
            except IntegrityError:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong>! Version name should be unique.")
                flash(message, 'danger')
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to save this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/branch.html',
                           form=form, selected=selected)


def import_data(categories: List[str], objects: List[DataItems], selected: str, version: Version) -> None:
    try:
        db.session.bulk_save_objects(objects, return_defaults=True)
        tmp = [TmpTable(item_id=obj.id,
                        node_name=selected,
                        category_id=cat) for obj, cat in zip(objects, categories)]
        db.session.bulk_save_objects(tmp)
    except Exception as ex:
        log.error(ex)
        db.session.rollback()
    else:
        # change status to STAGE which means that version is not empty
        version.status = 2
        db.session.commit()
    return


@datasets_blueprint.route('/import/<selected>', methods=['GET', 'POST'])
@login_required
def import2ds(selected):
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    if version.status == 3:
        abort(400)

    form = ImportForm(request.form)
    categories = Category.list(1, version.name)
    form.category.choices = [(-1, 'empty')] + [(i, cat.name) for i, cat in enumerate(categories)]
    scoring_models = Model.list(1, version.name)
    form.score_model.choices = [(-1, 'empty')] + [(i, model.name) for i, model in enumerate(scoring_models)]

    if request.method == 'POST':
        if form.validate_on_submit():
            label_ids = get_labels_of_version(version.id)
            if form.reason.data == 'moderation':
                pass
            else:
                if form.category_select.data == 'folder':
                    # send message to preprocessor
                    storage_dir = os.getenv("STORAGE_DIR")
                    task_id = str(uuid.uuid4())
                    while os.path.isdir(os.path.join(storage_dir, task_id)):
                        task_id = str(uuid.uuid4())
                    # TODO check if task_id already exist in database

                    label_ids = get_labels_of_version(version.id)
                    # TODO
                    # if not os.path.exists(form.flocation.data):
                    #     flash(f"No such file or directory: {form.flocation.data}", "error")
                    #     return redirect(f"/import/{selected}")
                    files = os.listdir(form.flocation.data)

                    # only directories
                    files = filter(
                        lambda x: os.path.isdir(x),
                        list(
                            map(
                                lambda x: os.path.join(form.flocation.data, x),
                                files
                            )
                        )
                    )
                    files = map(
                        lambda x: os.path.split(x)[-1],
                        list(files)
                    )

                    if not form.is_create_categs_from_folders and form.category_select.data == "folder":
                        for folder_name in files:
                            if folder_name not in label_ids:
                                flash(f"{folder_name} not in labels!", "error")

                    model_name = ''
                    if bool(form.is_score_model.data):
                        model = scoring_models[form.score_model.data]

                        model_name = model.local_chkpoint
                        _, model_name = os.path.split(model_name)

                    for proc in shortlife_processes:
                        if not proc.is_alive():
                            proc.terminate()

                    proc_to_copy_files = Process(
                        target=copy_directory,
                        args=(
                            form.flocation.data,
                            os.path.join(storage_dir, task_id),
                            task_id,
                            bool(form.is_size_control.data),
                            (int(form.min_size.data), int(form.min_size.data)),
                            bool(form.is_resize.data),
                            (int(form.resize_h.data), int(form.resize_w.data)),
                            bool(form.is_dedup.data),
                            label_ids,
                            selected,
                            bool(form.is_create_categs_from_folders),
                            bool(form.is_score_model.data),
                            model_name
                        ),
                        daemon=True
                    )
                    proc_to_copy_files.start()
                    shortlife_processes.append(proc_to_copy_files)
                    # proc_to_copy_files.join()

                    # если включена дедупликация, то сохранение нужно после
                    # процесса ручного отбора картинок (project/deduplication/views/def save_result)
                    # в противном случае - смотри rabbitmq_connector.py - воркер возвращает имена фалов
                    # отфильтрованных и ресайзнутых изображений

            # version.status = 2
            # db.session.commit()
            # TODO implement actual images import. For your convenience:
            print('flocation', form.flocation.data)
            print('reason', form.reason.data)
            print('category_select', form.category_select.data)
            print('category', form.category.data)
            print('is_score_model', bool(form.is_score_model.data))
            print('score_model', form.score_model.data)
            print('is_dedup', bool(form.is_dedup.data))
            print('is_size_control', bool(form.is_size_control.data))
            print('min_size', form.min_size.data)
            print('is_stub_control', bool(form.is_stub_control.data))
            print('is_valid_control', bool(form.is_valid_control.data))
            print('is_resize', bool(form.is_resize.data))
            print('resize_w', form.resize_w.data)
            print('resize_h', form.resize_w.data)
            print('general_category', form.general_category.data)

            # TODO update categories for current version, based on import results
            # return redirect(url_for('datasets.select', selected=version.name))
            return redirect(url_for(
                'deduplication.task_confirmation',
                task_id=task_id,
                selected=version.name,
                is_dedup=1 if bool(form.is_dedup.data) else 0
            ))
    return render_template('datasets/import.html', form=form, selected=selected, version=version)


@datasets_blueprint.route('/commit/<selected>', methods=['GET', 'POST'])
@login_required
def commit(selected):
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    if not version.actions_dict()['commit']:
        abort(400)
    form = CommitForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                commit_categories = prepare_to_commit(db.session, selected)
                # Незакомиченные из TmpTable - надо добавить в VersionItems и удалить из TmpTable
                items_to_commit = commit_categories.get("uncommited")
                try:
                    if len(items_to_commit):
                        db.session.bulk_save_objects(items_to_commit)
                    items_to_delete = commit_categories.get("uncommited_deleted")
                    if len(items_to_delete):
                        DataItems.query.filter(DataItems.id.in_(items_to_delete)).delete(synchronize_session=False)
                    # Изменения в уже закомиченных
                    commited_changed = commit_categories.get("commited_changed")
                    if len(commited_changed):
                        db.session.bulk_save_objects(commited_changed)
                    # Изменения для таблицы Diff (закомиченные)
                    deleted = commit_categories.get("commited_deleted")
                    if len(deleted):
                        db.session.bulk_save_objects(deleted)
                    # Внесли все изменения, чистим таблицы
                    TmpTable.query.filter_by(node_name=selected).delete()
                    Changes.query.filter_by(version_id=version.id).delete()
                    version.status = 3
                    db.session.commit()
                except Exception as ex:
                    app.logger.error(ex)
                    db.session.rollback()

                filepaths = [
                    DataItems.query.filter_by(id=item.item_id).first().path for item in items_to_commit
                ]
                task_id = str(uuid.uuid4())
                task_request = {
                    'id': task_id,
                    'type': 'merge_indexes',
                    'files_to_keep': filepaths
                }
                create_image_processing_task(task_request)

                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select',
                                        selected=version.name))
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to commit this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/commit.html',
                           form=form, selected=selected, version=version)


@datasets_blueprint.route('/merge/<selected>', methods=['GET', 'POST'])
@login_required
def merge(selected):
    child = Version.query.filter_by(name=selected).first()
    if child is None:
        abort(404)
    if child.status in [3]:
        abort(400)
    form = MergeForm(request.form)
    parents = Version.query.filter(Version.status == 3) \
        .order_by(Version.created_at.desc())
    form.target_select.choices = [(t.name, t.name)
                                  for t in parents
                                  if t.name != selected and
                                  not t.is_connected(child)]
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                version = Version.query.filter_by(name=form.target_select.data).first()
                if version.status in [1, 2]:
                    abort(400)
                vc = VersionChildren(child.id, version.id)
                db.session.add(vc)
                db.session.commit()
                # TODO -- update categories for merged branch
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.merge_categs',
                                        child=child.name,
                                        parent=version.name))
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to save this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/merge.html',
                           form=form, selected=selected)


@datasets_blueprint.route('/merge_categs/<parent>/<child>', methods=['GET', 'POST'])
@login_required
def merge_categs(parent, child):
    child = Version.query.filter_by(name=child).first()
    if child is None:
        abort(404)
    parent = Version.query.filter_by(name=parent).first()
    if parent is None:
        abort(404)
    if child.status in [3]:
        abort(400)
    categs = {}
    for task in Category.TASKS():
        child_categs = Category.list(task[0], child.name)
        parent_categs = Category.list(task[0], parent.name)
        categs[task[0]] = {}
        categs[task[0]]['child'] = child_categs
        categs[task[0]]['parent'] = parent_categs
    if request.method == 'POST':
        merged_list = {}
        is_error = False
        for task in Category.TASKS():
            task_categs_seq = []
            for ch_c in categs[task[0]]['child']:
                try:
                    pos = int(request.values['categ_%d' % ch_c.id])
                    task_categs_seq.append((pos, ch_c))
                except Exception:
                    pass
            for pa_c in categs[task[0]]['parent']:
                try:
                    pos = int(request.values['categ_%d' % pa_c.id])
                    task_categs_seq.append((pos, pa_c))
                except Exception:
                    pass
            task_categs_seq.sort(key=lambda o: o[0])
            checking_validity_list = [o[0] for o in task_categs_seq]
            if list(range(len(checking_validity_list))) != checking_validity_list:
                message = Markup(
                    "<strong>" + task[1] + "</strong> Wrong positions sequence: " + str(checking_validity_list))
                flash(message, 'danger')
                is_error = True
            else:
                merged_list[task[0]] = task_categs_seq
        if not is_error:
            try:
                # Insert categories for merged branch
                for task in Category.TASKS():
                    for d_categ in Category.list(task[0], child.name):
                        db.session.delete(d_categ)
                    for t_categ in merged_list[task[0]]:
                        categ = Category(t_categ[1].name,
                                         child.id,
                                         task[0],
                                         t_categ[1].description,
                                         t_categ[0])
                        db.session.add(categ)
                db.session.commit()
                message = Markup("Saved successfully!")
                flash(message, 'success')
                return redirect(url_for('datasets.select',
                                        selected=child.name))
            except Exception as e:
                traceback.print_exc()
                db.session.rollback()
                message = Markup(
                    "<strong>Error!</strong> Unable to save this version. " + str(e))
                flash(message, 'danger')
    return render_template('datasets/merge_categs.html',
                           categs=categs,
                           tasks=dict(Category.TASKS()),
                           child=child, parent=parent)


@datasets_blueprint.route('/checkout/<selected>', methods=['GET', 'POST'])
@login_required
def checkout(selected):
    """
    Получить список DataItems выбранной версии
    для обучения в kuberflow
    """
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    nodes = get_nodes_above(db.session, version.id)
    data_items = get_items_of_nodes_with_label(nodes)
    task = upload_files_to_storage.delay(
        version.name,
        data_items
    )
    return redirect(url_for('datasets.select', selected=version.name))


@datasets_blueprint.route('/split/<selected>', methods=['GET', 'POST'])
@login_required
def split(selected):
    version = Version.query.filter_by(name=selected).first()
    if version is None:
        abort(404)
    if version.status == 3:
        abort(400)
    form = SplitForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            # Берем data_items только от текущей ноды
            # TODO: получить все ранее не распределенные
            data_items = get_uncommited_items(db.session, version.name)
            train_size = form.train_size.data
            val_size = form.val_size.data
            test_size = form.test_size.data
            sum = round(train_size + val_size + test_size, 2)
            if sum != 1:
                message = Markup(
                    f"<strong>Train size + test size + val size must be equal to 1.\nSum: {sum}")
                flash(message, 'danger')
            else:
                train_items, val_items, test_items = split_data_items(data_items, train_size, val_size)
                tmp_ds = []
                for item in train_items:
                    upd_tmp_item = dict(
                        itm_id=item.id,
                        node=selected,
                        ds=0
                    )
                    tmp_ds.append(upd_tmp_item)
                for item in val_items:
                    upd_tmp_item = dict(
                        itm_id=item.id,
                        node=selected,
                        ds=1
                    )
                    tmp_ds.append(upd_tmp_item)
                for item in test_items:
                    upd_tmp_item = dict(
                        itm_id=item.id,
                        node=selected,
                        ds=2
                    )
                    tmp_ds.append(upd_tmp_item)
                try:
                    update_tmp(db, tmp_ds)
                    db.session.commit()
                    message = Markup(
                        f"<strong>Save successfully")
                    flash(message, 'success')
                except Exception as ex:
                    log.error(ex)
                    db.session.rollback()
                return redirect(url_for('datasets.select',
                                        selected=version.name))
    return render_template(
        'datasets/split.html',
        version=version,
        form=form
    )


if __name__ == '__main__':
    # data_items = get_items_of_nodes([8, 9])
    # print(data_items)
    items = get_items_of_nodes_with_label([8, 9])
    print(items)
