from project import db, bcrypt
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from datetime import datetime
import re


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
    status = db.Column(db.SmallInteger, nullable=False) # 1=empty 2=stage 3=versioned
    child_id = db.Column(db.Integer, nullable=True)
    description = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
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
        self.status = 1 #empty
        self.child_id = None
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
        TPL1 = '%(id)s[URL="%(prefix)s/%(id)s", style="bold"];\n'
        TPL2 = '%(id)s[URL="%(prefix)s/%(id)s"];'
        out = []
        for v in Version.versions():
            if v.name == sel:
                out.append(TPL1 % dict(id=v.name, prefix=url_prefix))
            else:
                out.append(TPL2 % dict(id=v.name, prefix=url_prefix))
        return ''.join(out)
    
    @staticmethod
    def edges():
        TPL = "%s->%s;\n"
        out = []
        for v in Version.versions():
            if v.child_id is not None:
                child = Version.query.get(v.child_id)
                out.append(TPL % (v.name, child.name))
        return ''.join(out)
    
    @staticmethod
    def dot_str( sel):
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
        elif self.status == 2:
            out['init'] = True
            out['edit'] = True
            out['import'] = True
            out['split'] = True
            out['commit'] = True
            out['browse'] = True
        elif self.status == 3:
            out['branch'] = True
            out['merge'] = True
            out['init'] = True
            out['checkout'] = True
            out['browse'] = True
        return out