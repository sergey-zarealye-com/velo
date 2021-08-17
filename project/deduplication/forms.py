from flask_wtf import FlaskForm
from wtforms import (
    SubmitField
)


class TestForm(FlaskForm):
    submit_btn = SubmitField()
    delete_btn = SubmitField()
