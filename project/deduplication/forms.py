from flask_wtf import FlaskForm
from wtforms import (
    SubmitField
)
from wtforms.validators import DataRequired, Length, NumberRange

class TestForm(FlaskForm):
    submit_btn = SubmitField()
    delete_btn = SubmitField()
