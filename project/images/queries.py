import time
from collections import namedtuple
from contextlib import closing
from typing import List, Dict
from sqlalchemy import update, and_, func
from sqlalchemy import bindparam
from collections import Counter
from project.models import DataItems, VersionItems, Category, TmpTable, Version, Diff, Changes

version_item = namedtuple("VersionItem", "id,version,path,label,class_id,ds,priority")


def get_commited_categories_count(sess, version_id: List[int]):
    deleted_items = Diff \
        .query \
        .filter(Diff.version_id.in_(version_id)) \
        .with_entities(Diff.item_id) \
        .all()
    return dict(sess.query(VersionItems.category_id, func.count(VersionItems.category_id)) \
        .filter(VersionItems.version_id.in_(version_id)) \
        .filter(VersionItems.item_id.notin_(deleted_items)) \
        .group_by(VersionItems.category_id).all())


def get_commited_set_count(sess, version_id: List[int]):
    deleted_items = Diff \
        .query \
        .filter(Diff.version_id.in_(version_id)) \
        .with_entities(Diff.item_id) \
        .all()
    return dict(sess.query(VersionItems.ds_type, func.count(VersionItems.ds_type)) \
        .filter(VersionItems.version_id.in_(version_id)) \
        .filter(VersionItems.item_id.notin_(deleted_items)) \
        .group_by(VersionItems.ds_type).all())


def get_items_of_version(sess, version_id: List[int], page, items) -> List[version_item]:
    """Если в старшем версии датасета изменен класс, возвращется только последняя запись"""
    deleted_items = Diff \
        .query \
        .filter(Diff.version_id.in_(version_id)) \
        .with_entities(Diff.item_id) \
        .all()
    query = sess.query(VersionItems, DataItems, Category) \
        .filter(VersionItems.version_id.in_(version_id)) \
        .join(DataItems) \
        .filter(Category.id == VersionItems.category_id) \
        .filter(DataItems.id.notin_(deleted_items)) \
        .order_by(DataItems.id, VersionItems.version_id.desc()) \
        .distinct(DataItems.id).limit(items).offset((page - 1) * items)
    return [version_item(item.DataItems.id,
                         item.VersionItems.version_id,
                         item.DataItems.path,
                         item.Category.name,
                         item.Category.id,
                         item.VersionItems.ds_type if item.VersionItems.ds_type is not None else 3,
                         item.VersionItems.priority
                         ) for item in query.all()]


def get_changed_items(sess, node_id: int) -> Dict:
    query = sess.query(Changes, Category) \
        .filter(Changes.version_id == node_id)
    query = query.join(Category, Category.id == Changes.new_category, isouter=True)
    res = query.all()
    changed_items = {}
    for item in res:
        if item.Category:
            changed_items[item.Changes.item_id] = {'id': item.Category.id,
                                                   'label': item.Category.name,
                                                   'priority': item.Changes.priority}
        else:
            changed_items[item.Changes.item_id] = {'id': None,
                                                   'label': 'deleted',
                                                   'priority': item.Changes.priority}

    return changed_items


def get_id_by_name(node_name: str) -> int:
    id = Version \
        .query \
        .filter(Version.name == node_name) \
        .with_entities(Version.id) \
        .first()
    return id.id

def get_uncommited_categories_count(sess, node_name):
    return dict(sess.query(TmpTable.category_id, func.count(TmpTable.category_id))\
        .filter(TmpTable.node_name == node_name)\
        .group_by(TmpTable.category_id).all())

def get_uncommited_set_count(sess, node_name):
    return dict(sess.query(TmpTable.ds_type, func.count(1))\
        .filter(TmpTable.node_name == node_name)\
        .group_by(TmpTable.ds_type).all())

def get_uncommited_items(sess, node_name: str, page = None, items = None) -> List[version_item]:
    """Возвращает version_item для текущей ноды из таблицы TmpTable"""
    node_id = get_id_by_name(node_name)
    query = sess.query(TmpTable, DataItems, Category) \
        .filter(TmpTable.node_name == node_name) \
        .join(DataItems) \
        .filter(Category.id == TmpTable.category_id)
    if page is not None and items is not None:
        query = query.limit(items).offset((page - 1) * items)
    return [version_item(item.DataItems.id,
                         node_id,
                         item.DataItems.path,
                         item.Category.name,
                         item.Category.id,
                         item.DataItems.tmp[0].ds_type if item.DataItems.tmp[0].ds_type is not None else 3,
                         item.TmpTable.priority
                         ) for item in query.all()]


def get_unsplitted_items(sess, node_name: str) -> List[version_item]:
    """Возвращает version_item, для которых не задан тип датасета"""
    node_id = get_id_by_name(node_name)
    query = sess.query(TmpTable, DataItems, Category) \
        .filter(TmpTable.node_name == node_name) \
        .filter(TmpTable.ds_type == None) \
        .join(DataItems) \
        .filter(Category.id == TmpTable.category_id)
    return [version_item(item.DataItems.id,
                         node_id,
                         item.DataItems.path,
                         item.Category.name,
                         item.Category.id,
                         3,
                         item.TmpTable.priority
                         ) for item in query.all()]


def update_changes(db, changes: List[Dict]) -> None:
    """Обновить записи в таблице изменений"""
    stmt = (
        update(Changes).
            where(
            and_(
                Changes.version_id == bindparam('v_id'),
                Changes.item_id == bindparam('itm_id'))).
            values(new_category=bindparam('category'), priority=bindparam('pr'))
    )
    with db.engine.begin() as conn:
        conn.execute(
            stmt,
            changes
        )
    return

def get_ds_info(session, nodes_of_version, selected):
    dict_uncommited_categories = get_uncommited_categories_count(session, selected)
    dict_uncommited_set = get_uncommited_set_count(session, selected)
    dict_commited_categories = get_commited_categories_count(session, nodes_of_version)
    dict_commited_set = get_commited_set_count(session, nodes_of_version)
    for cur_dict in [dict_commited_set, dict_uncommited_set]:
        if None in cur_dict:
            cur_dict[3] = cur_dict[None]
            cur_dict.pop(None, None)
    set_info = dict(Counter(dict_commited_set) + Counter(dict_uncommited_set))
    categories_info = dict(Counter(dict_commited_categories) + Counter(dict_uncommited_categories))

    return set_info, \
           categories_info, \
           sum(dict_uncommited_categories.values()), \
           sum(dict_commited_categories.values())


if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from project.models import VersionChildren

    def get_nodes_above(sess, node_id) -> List[int]:
        """Возвращает id нод от текущей (включая текущую)"""
        topq = sess.query(VersionChildren)
        topq = topq.filter(VersionChildren.child_id == node_id)
        # check for root
        top_res = topq.first()
        if top_res is None:
            return [node_id]
        topq = topq.cte('cte', recursive=True)

        bottomq = sess.query(VersionChildren)
        bottomq = bottomq.join(topq, VersionChildren.child_id == topq.c.parent_id)

        recursive_q = topq.union(bottomq)
        q = sess.query(recursive_q).all()
        return sorted(list(set([item for t in q for item in t])))

    engine = create_engine("postgresql://velo:123@localhost:5432/velo")
    Session = sessionmaker(bind=engine)
    session = Session()
    version_id = 5
    page, items = 1, 50
    selected = "train"
    time_S = time.time()
    nodes_of_version = get_nodes_above(session, version_id)
    timeA = time.time()
    get_ds_info(session, nodes_of_version, selected)
    print(f'get_ds_info {time.time() - timeA}')
    timeA = time.time()
    version_items = get_items_of_version(session, nodes_of_version, page, items)
    print(f'get_items_of_version {time.time() - timeA}')
    timeA = time.time()
    uncommitted_items = get_uncommited_items(session, selected, page, items)
    print(f'get_uncommited_items {time.time() - timeA}')
    timeA = time.time()
    print(f'done: {time.time()-time_S}')
    with closing(session) as sess:
        res = get_unsplitted_items(session, "train")

