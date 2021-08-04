from collections import namedtuple
from contextlib import closing
from typing import List, Dict

from sqlalchemy import update, and_
from sqlalchemy import bindparam

from project.models import DataItems, VersionItems, Category, TmpTable, Version, Diff, Changes

version_item = namedtuple("VersionItem", "id,version,path,label,class_id")


def get_items_of_version(sess, version_id: List[int]) -> List[version_item]:
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
        .distinct(DataItems.id)
    return [version_item(item.DataItems.id,
                         item.VersionItems.version_id,
                         item.DataItems.path,
                         item.Category.name,
                         item.Category.id
                         ) for item in query.all()]


def get_changed_items(sess, node_id: int) -> Dict:
    query = sess.query(Changes, Category) \
        .filter(Changes.version_id == node_id)
    query = query.join(Category, Category.id == Changes.new_category, isouter=True)
    res = query.all()
    changed_items = {}
    for item in res:
        if item.Category:
            changed_items[item.Changes.item_id] = item.Category.name
        else:
            changed_items[item.Changes.item_id] = None
    return changed_items


def get_id_by_name(node_name: str) -> int:
    id = Version \
        .query \
        .filter(Version.name == node_name) \
        .with_entities(Version.id) \
        .first()
    return id.id


def get_uncommited_items(sess, node_name: str) -> List[version_item]:
    node_id = get_id_by_name(node_name)
    query = sess.query(TmpTable, DataItems, Category) \
        .filter(TmpTable.node_name == node_name) \
        .join(DataItems) \
        .filter(Category.id == TmpTable.category_id)
    return [version_item(item.DataItems.id,
                         node_id,
                         item.DataItems.path,
                         item.Category.name,
                         item.Category.id,
                         ) for item in query.all()]


def update_changes(db, changes: List[Dict]) -> None:
    """Обновить записи в таблице изменений"""
    stmt = (
        update(Changes).
            where(
            and_(
                Changes.version_id == bindparam('v_id'),
                Changes.item_id == bindparam('itm_id'))).
            values(new_category=bindparam('category'))
    )
    with db.engine.begin() as conn:
        conn.execute(
            stmt,
            changes
        )
    return


if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("postgresql://velo:123@localhost:5432/velo")
    Session = sessionmaker(bind=engine)
    session = Session()
    with closing(session) as sess:
        # res = get_items_of_version_with_changes(sess, [2, 3])
        res = get_items_of_version(session, [1, 2])
        for item in res:
            print(f"Item id: {item.id}")
            print(f"Item path: {item.path}")
            print(f"Version id: {item.version}")
            print(f"Label: {item.label}")
