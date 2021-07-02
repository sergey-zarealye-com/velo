from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Length

class EditVersionForm(FlaskForm):
    name = StringField('Name', 
                     validators=[DataRequired(),
                                 Length(min=1, max=254)])
    description = StringField('Description', 
                     validators=[Length(min=0, max=254)])
    
