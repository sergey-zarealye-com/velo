from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Length, EqualTo, Email

class NewBatchForm(FlaskForm):
    src = StringField('Source file path', 
                     validators=[DataRequired(),
                                 Length(min=8, max=1024)])