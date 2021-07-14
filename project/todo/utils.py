import re
from project import db
from project.models import Moderation, ToDoItem


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


# def prepare_todo_list(form):
#     q = Moderation.query.distinct("src").all()
#     for i, t in enumerate(q):
#         title = t.src.split(sep='/')[-1]
#         todo = ToDoItem.query.filter_by(title=title).first()
#         if todo is None:
#             todo = ToDoItem(file_path=t.src, title=title, description='Description', gt_category=form.general_category)
#             db.session.add(todo)
#     db.session.commit()
