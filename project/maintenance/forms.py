from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, Email

class AddCategoryForm(FlaskForm):
    name = StringField('Name', 
                     validators=[DataRequired(),
                                 Length(min=1, max=254)])
    description = TextAreaField('Description')
    
class EditCategoryForm(FlaskForm):
    name = StringField('Name', 
                     validators=[DataRequired(),
                                 Length(min=1, max=254)])
    description = TextAreaField('Description')

class AddModelForm(FlaskForm):
    name = StringField('Name', 
                     validators=[DataRequired(),
                                 Length(min=1, max=254)])
    description = TextAreaField('Description')
    kf_uid = StringField('Kubeflow UID')
    local_chkpoint = StringField('Path to model checkpoint file')
    
class EditModelForm(AddModelForm):
    pass
        