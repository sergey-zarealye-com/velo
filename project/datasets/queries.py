from typing import List, Dict
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

from project.images.queries import get_id_by_name
from project.models import VersionChildren, DataItems, VersionItems, Category, TmpTable, Changes, Diff


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


def get_items_of_nodes(node_ids: List[int]) -> List[DataItems]:
    item_ids = VersionItems \
        .query \
        .filter(VersionItems.version_id.in_(node_ids)) \
        .with_entities(VersionItems.item_id) \
        .all()
    return DataItems.query.filter(DataItems.id.in_(item_ids)).all()


def get_labels_of_version(version: int) -> Dict[str, int]:
    """
    return: {'erotic': 0, 'fighting': 1, ...}
    """
    labels = Category.query.filter(Category.version_id == version).with_entities(Category.name, Category.id).all()
    return {item.name: item.id for item in labels}


def prepare_to_commit(sess, node_name) -> Dict:
    """Возвращает словарь, где все измененные data_items раскиданы по категориям"""
    res = dict(
        uncommited=list(),
        uncommited_deleted=list(),
        commited_changed=list(),
        commited_deleted=list()
    )
    # Незакомиченные измененные
    query = sess.query(TmpTable, Changes) \
        .filter(TmpTable.node_name == node_name)
    query = query.join(Changes, Changes.item_id == TmpTable.item_id)
    ids = []
    for item in query.all():
        # -1 - признак удаленности
        if item.Changes.new_category != -1:
            obj = VersionItems(item_id=item.Changes.item_id,
                               version_id=item.Changes.version_id,
                               category_id=item.Changes.new_category)
            res['uncommited'].append(obj)
        else:
            res['uncommited_deleted'].append(item.Changes.item_id)
        ids.append(item.Changes.item_id)
    # Незакомиченные и неизмененные
    version_id = get_id_by_name(node_name)
    query = sess.query(TmpTable) \
        .filter(
        and_(
            TmpTable.node_name == node_name,
            TmpTable.item_id.notin_(ids))
    )
    for item in query.all():
        obj = VersionItems(item_id=item.item_id,
                           version_id=version_id,
                           category_id=item.category_id)
        res['uncommited'].append(obj)
    # Закомиченные измененные
    # Закомиченный item есть в таблице changes в заданной версии, но его нет в таблицу Tmp
    tmp_items = TmpTable \
        .query \
        .filter(TmpTable.node_name == node_name) \
        .with_entities(TmpTable.item_id)
    tmp_ids = [item.item_id for item in tmp_items.all()]
    changed_item_ids = Changes \
        .query \
        .filter(Changes.version_id == version_id)
    for item in changed_item_ids.all():
        if item.item_id not in tmp_ids:
            if item.new_category != -1:
                vi = VersionItems(item_id=item.item_id,
                                  version_id=item.version_id,
                                  category_id=item.new_category)
                res['commited_changed'].append(vi)
            else:
                diff = Diff(version_id=version_id, item_id=item.item_id)
                res['commited_deleted'].append(diff)
    return res


if __name__ == '__main__':
    engine = create_engine("postgresql://velo:123@localhost:5432/velo")
    Session = sessionmaker(bind=engine)
    session = Session()

    prepare_to_commit(session, "v2")
