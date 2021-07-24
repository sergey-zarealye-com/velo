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
    