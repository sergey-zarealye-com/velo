from typing import List, Dict

from project.models import VersionChildren, DataItems, VersionItems, Category


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


if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from project.models import Category, Moderation

    engine = create_engine("postgresql://velo:123@localhost:5432/velo")
    Session = sessionmaker(bind=engine)
    session = Session()

    res = get_nodes_above(session, 2)
    items = get_items_of_nodes(res)
