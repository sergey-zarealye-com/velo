from typing import Optional
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy.orm import relationship

from project import db, bcrypt
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import and_, or_
from datetime import datetime
import re
from enum import Enum


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String, unique=True, nullable=False)
    _password = db.Column(db.Binary(60), nullable=False)
    authenticated = db.Column(db.Boolean, default=False)
    email_confirmation_sent_on = db.Column(db.DateTime, nullable=True)
    email_confirmed = db.Column(db.Boolean, nullable=True, default=False)
    email_confirmed_on = db.Column(db.DateTime, nullable=True)
    registered_on = db.Column(db.DateTime, nullable=True)
    last_logged_in = db.Column(db.DateTime, nullable=True)
    current_logged_in = db.Column(db.DateTime, nullable=True)
    role = db.Column(db.String, default='user')

    def __init__(self, email, password, email_confirmation_sent_on=None, role='user'):
        self.email = email
        self.password = password
        self.authenticated = False
        self.email_confirmation_sent_on = email_confirmation_sent_on
        self.email_confirmed = False
        self.email_confirmed_on = None
        self.registered_on = datetime.now()
        self.last_logged_in = None
        self.current_logged_in = datetime.now()
        self.role = role

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = bcrypt.generate_password_hash(password)

    @hybrid_method
    def is_correct_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    @property
    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated

    @property
    def is_active(self):
        """Always True, as all users are active."""
        return True

    @property
    def is_email_confirmed(self):
        """Return True if the user confirmed their email address."""
        return self.email_confirmed

    @property
    def is_anonymous(self):
        """Always False, as anonymous users aren't supported."""
        return False

    def get_id(self):
        """Return the email address to satisfy Flask-Login's requirements."""
        """Requires use of Python 3"""
        return str(self.id)

    def __repr__(self):
        return '<User {}>'.format(self.email)


class Version(db.Model):
    __tablename__ = 'versions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, unique=True, nullable=False)
    status = db.Column(db.SmallInteger, nullable=False)  # 1=empty 2=stage 3=versioned
    description = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship("User")

    """
        Status defines allowed operations according to state diagram https://bit.ly/3x9Uv6e
        
        digraph G {
 start->empty [label="Init (new v.)"];
 empty->stage [label=Import];
 stage->stage [label=Import];
 stage->versioned [label=Commit];
 versioned->versioned [label=Checkout];
 stage->stage [label=Split];
 versioned->stage [label="Branch (new v.)"];
 versioned->stage [label="Merge (into or new v.)"];
 empty->empty [label="Init (new v.)"];
 stage->empty [label="Init (new v.)"];
 versioned->empty [label="Init (new v.)"];
 empty->empty [label="Edit"];
 stage->stage [label="Edit"];
}
    """

    def __init__(self, name, description, user_id):
        self.name = Version.safe_id(name)
        self.description = description
        self.user_id = user_id
        self.status = 1  # empty
        self.created_at = datetime.now()

    @staticmethod
    def safe_id(s):
        tokens = re.findall(r'\w+', s)
        if len(tokens):
            if len(re.findall(r'^\d', tokens[0])):
                tokens[0] = '_' + tokens[0]
            return ('_'.join(tokens)).lower()
        else:
            raise Exception('Illegal name')

    @staticmethod
    def versions():
        return Version.query.all()

    @staticmethod
    def get_first():
        return Version.query.first()

    @staticmethod
    def nodes_def(sel, url_prefix='/datasets/select'):
        STYLE_SEL = 'filled'
        COLOR = 'white'
        COLOR_SEL = 'lightgrey'
        STYLE_COMMIT = 'bold'
        TPL = '%(id)s[URL="%(prefix)s/%(id)s", style="%(style)s", fillcolor="%(color)s"];\n'
        out = []
        for v in Version.versions():
            style = []
            color = COLOR
            if v.name == sel:
                style.append(STYLE_SEL)
                color = COLOR_SEL
            if v.status == 3:
                style.append(STYLE_COMMIT)
            out.append(TPL % dict(id=v.name,
                                  prefix=url_prefix,
                                  style=','.join(style),
                                  color=color))
        return ''.join(out)

    @staticmethod
    def edges():
        TPL = "%s->%s;\n"
        out = []
        for v in Version.versions():
            children = VersionChildren.query.filter_by(parent_id=v.id)
            for child in children:
                ch = Version.query.get(child.child_id)
                if ch is not None:
                    out.append(TPL % (v.name, ch.name))
        return ''.join(out)

    @staticmethod
    def dot_str(sel):
        TPL = """digraph "dsvers" {
        %s
        %s
        }"""
        return TPL % (Version.nodes_def(sel), Version.edges())

    def actions_dict(self):
        actions = ['init', 'edit', 'import', 'split', 'commit',
                   'branch', 'merge', 'checkout', 'browse']
        out = dict([(a, False) for a in actions])
        if self.status == 1:
            out['init'] = True
            out['edit'] = True
            out['import'] = True
            out['merge'] = True
            out['commit'] = True
        elif self.status == 2:
            out['init'] = True
            out['edit'] = True
            out['import'] = True
            out['split'] = True
            out['commit'] = True
            out['browse'] = True
            out['merge'] = True
        elif self.status == 3:
            out['branch'] = True
            out['init'] = True
            out['checkout'] = True
            out['browse'] = True
        return out

    def is_connected(self, child):
        edge = VersionChildren.query.filter_by(child_id=child.id,
                                               parent_id=self.id).first()
        return edge is not None

    def categs_no(self):
        out = []
        for task in Category.TASKS():
            cl = Category.list(task[0], self.name)
            out.append(task[1])
            out.append(': <a href="/maintenance/categs_list/' + self.name + '">')
            out.append(str(len(cl)))
            out.append('</a> ')
        return ''.join(out)

    def data_no(self):
        return str(VersionItems.query.filter_by(version_id=self.id).count())

    def parent(self):
        vc = VersionChildren.query.filter_by(child_id=self.id).first()
        if vc is None:
            return None
        else:
            return Version.query.get(vc.parent_id)


class VersionChildren(db.Model):
    __tablename__ = 'version_children'
    child_id = db.Column(db.Integer, db.ForeignKey('versions.id'), nullable=False, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('versions.id'), nullable=False, primary_key=True)
    child = db.relationship("Version", foreign_keys=[child_id])
    parents = db.relationship("Version", foreign_keys=[parent_id])
    __table_args__ = (
        PrimaryKeyConstraint('child_id', 'parent_id'),
    )

    def __init__(self, child_id, parent_id):
        self.child_id = child_id
        self.parent_id = parent_id


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    version_id = db.Column(db.Integer, db.ForeignKey('versions.id'), nullable=False)
    name = db.Column(db.String, unique=False, nullable=False)
    task = db.Column(db.SmallInteger, nullable=False)  # 1=CV classes, 2=NLP classes
    position = db.Column(db.Integer, nullable=False)  # position related to Model outputs, numbering starts from ZERO
    description = db.Column(db.String, nullable=True)

    version = db.relationship("Version")

    @staticmethod
    def TASKS():
        return [(1, 'Vision'),
                (2, 'NLP')]

    def __init__(self, name, version_id, task, description=None, position=None):
        self.name = name
        self.version_id = version_id

        self.task = task
        self.description = description
        if position is not None:
            self.position = position
        else:
            last_categ = Category.get_last(version_id, task)
            if last_categ is None:
                self.position = 0
            else:
                self.position = last_categ.position + 1

    @staticmethod
    def get_last(version_id, task):
        return Category.query \
            .filter_by(version_id=version_id, task=task) \
            .order_by(Category.position.desc()) \
            .first()

    @staticmethod
    def list(task, version_name):
        version = Version.query.filter_by(name=version_name).first()
        if version is None:
            return []
        return Category.query \
            .filter_by(version_id=version.id, task=task) \
            .order_by(Category.position) \
            .all()


class DataItems(db.Model):
    __tablename__ = 'data_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    path = db.Column(db.String, unique=True, nullable=False)
    vi = relationship(
        "VersionItems", back_populates="data_item",
        cascade="all, delete",
        passive_deletes=True
    )
    tmp = relationship(
        "TmpTable", back_populates="data_item",
        cascade="all, delete",
        passive_deletes=True
    )
    d = relationship(
        "Diff", back_populates="data_item",
        cascade="all, delete",
        passive_deletes=True
    )
    c = relationship(
        "Changes", back_populates="data_item",
        cascade="all, delete",
        passive_deletes=True
    )

    def add_if_not_exists(path: str) -> int:
        entry = DataItems.query.filter_by(path=path).first()

        if entry:
            return entry.id

        entry = DataItems(path=path)
        db.session.add(entry)
        db.session.flush()

        return entry.id


class VersionItems(db.Model):
    __tablename__ = 'version_items'
    item_id = db.Column(db.Integer, db.ForeignKey('data_items.id', ondelete='CASCADE'), nullable=False)
    version_id = db.Column(db.Integer, db.ForeignKey('versions.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    data_item = relationship("DataItems", back_populates="vi")
    __table_args__ = (
        PrimaryKeyConstraint('item_id', 'version_id'),
    )


class TmpTable(db.Model):
    __tablename__ = 'tmp_table'
    item_id = db.Column(db.Integer, db.ForeignKey('data_items.id', ondelete='CASCADE'), nullable=False)
    node_name = db.Column(db.String, db.ForeignKey('versions.name'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    data_item = relationship("DataItems", back_populates="tmp")
    __table_args__ = (
        PrimaryKeyConstraint('item_id', 'node_name'),
    )


class Moderation(db.Model):
    __tablename__ = 'moderation'
    src = db.Column(db.String, nullable=False, unique=False)
    file = db.Column(db.String, nullable=False, unique=False)
    src_media_type = db.Column(db.String, nullable=False)
    category = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    title = db.Column(db.String, nullable=True)
    id = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint('src', 'file'),
    )


class ToDoItem(db.Model):
    __tablename__ = 'todo_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    version_id = db.Column(db.Integer, db.ForeignKey('versions.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    file_path = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, unique=False, nullable=True)
    description = db.Column(db.String, unique=False, nullable=True)
    audio_text = db.Column(db.String, unique=False, nullable=True)
    gt_category = db.Column(db.String, unique=False, nullable=False)
    assigned_categories_json = db.Column(db.String, unique=False, nullable=True)

    user = db.relationship("User")
    version = db.relationship("Version")

    def __init__(self, file_path, title, description, gt_category, id):
        self.file_path = file_path
        self.title = title
        self.description = description
        self.gt_category = gt_category
        self.created_at = datetime.now()
        self.id = id
        self.user_id = None
        self.version_id = None
        self.assigned_categories_json = None

    @staticmethod
    def fetch_for_user(user_id, skip=0, limit=25):
        return ToDoItem.query.filter(or_(
            ToDoItem.started_at.is_(None),
            and_(
                ToDoItem.started_at.isnot(None),
                ToDoItem.finished_at.is_(None),
                ToDoItem.user_id == user_id
            )
        )).order_by(ToDoItem.created_at) \
            .limit(limit).offset(skip)


class DeduplicationStatus(Enum):
    staged = "Staged"
    processing = "Processing"
    finished = "Processing is finished"
    taken = "Taken"
    submited = "Submited"


class Deduplication(db.Model):
    __tablename__ = 'deduplication'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_uid = db.Column(db.String)
    celery_task_id = db.Column(db.String)  # to access task result and status if service has restarted
    # user who has created this task
    # user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stages_status = db.Column(JSON)
    result = db.Column(JSON)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True, default=None)
    task_status = db.Column(db.String, default=DeduplicationStatus.staged.value)
    create_missing_categories = db.Column(db.Boolean)


class Diff(db.Model):
    __tablename__ = 'diff'
    version_id = db.Column(db.Integer, db.ForeignKey('versions.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('data_items.id', ondelete='CASCADE'), nullable=False)
    data_item = relationship("DataItems", back_populates="d")
    __table_args__ = (
        PrimaryKeyConstraint('version_id', 'item_id'),
    )


class CeleryTask(db.Model):
    __tablename__ = 'celerytasks'
    task_id = db.Column(db.String, primary_key=True, nullable=False)

    def __init__(self, task_id):
        self.task_id = task_id


class Changes(db.Model):
    __tablename__ = 'changes'
    version_id = db.Column(db.Integer, db.ForeignKey('versions.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('data_items.id', ondelete='CASCADE'), nullable=False)
    new_category = db.Column(db.Integer, nullable=False)
    data_item = relationship("DataItems", back_populates="c")
    __table_args__ = (
        PrimaryKeyConstraint('version_id', 'item_id'),
    )
