from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange

class EditVersionForm(FlaskForm):
    name = StringField('Name', 
                     validators=[DataRequired(),
                                 Length(min=1, max=254)])
    description = StringField('Description', 
                     validators=[Length(min=0, max=254)])
    
class ImportForm(FlaskForm):
    flocation = StringField('Tar/Dir/Bucket path', 
                            validators=[DataRequired(),
                            Length(min=1, max=1024)])
    reason = SelectField('Reason', 
                            choices=[('general', 'General'),
                                     ('moderation', 'Moderation')], 
                            coerce=str)
    category_select = SelectField('Category assignment', 
                            choices=[('folder', 'From folder name'),
                                     ('set', 'Set category')], 
                            coerce=str)
    category = SelectField('Category', #TODO -- shall be dynamic!!!
                            choices=[(1, 'Cats'),
                                     (2, 'Dogs')], 
                            coerce=int)
    is_score_model = BooleanField('Score imported images')
    score_model = SelectField('Classification model', #TODO -- shall be dynamic!!!
                            choices=[(1, 'ResNet'),
                                     (2, 'EfficientNet')], 
                            coerce=int)
    is_dedup = BooleanField('Check for duplicates')
    is_size_control = BooleanField('Check for minimal image size')
    min_size = IntegerField('Minimal image size', default=224, 
                                  validators=[NumberRange(min=64, max=4096)])
    is_stub_control = BooleanField('Check for image placeholders')
    is_valid_control = BooleanField('Check for image validity')
    is_resize = BooleanField('Resize images')
    resize_w = IntegerField('Width', default=256, 
                                  validators=[NumberRange(min=64, max=4096)])
    resize_h = IntegerField('Height', default=256, 
                                  validators=[NumberRange(min=64, max=4096)])
    
class CommitForm(FlaskForm):
    pass

class MergeForm(FlaskForm):
    target_select = SelectField('Merge from', coerce=str)
    
    