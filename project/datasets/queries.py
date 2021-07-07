from typing import List

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


if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("postgresql://velo:123@localhost:5432/velo")
    Session = sessionmaker(bind=engine)
    session = Session()
    nodes = get_nodes_above(session, 2)

    print(nodes)
