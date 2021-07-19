from collections import namedtuple
from typing import List

from project.models import DataItems, VersionItems, Category

version_item = namedtuple("VersionItem", "id,version,path,label")


def get_items_of_version(sess, version_id: List[int]) -> List[version_item]:
    query = sess.query(VersionItems, DataItems, Category) \
        .filter(VersionItems.version_id.in_(version_id)) \
        .join(DataItems) \
        .filter(Category.id == VersionItems.category_id)
    return [version_item(item.DataItems.id,
                         item.VersionItems.version_id,
                         item.DataItems.path,
                         item.Category.name) for item in query.all()]


if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("postgresql://velo:123@localhost:5432/velo")
    Session = sessionmaker(bind=engine)
    session = Session()

    res = get_items_of_version(session, [1, 2])
    for item in res:
        print(f"Item id: {item.id}")
        print(f"Item path: {item.path}")
        print(f"Version id: {item.version}")
        print(f"Label: {item.label}")
