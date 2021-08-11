from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    BooleanField,
    IntegerField,
    FloatField
)
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
    is_create_categs_from_folders = BooleanField('Create categories if missing')
    category = SelectField('Category',  # TODO -- shall be dynamic!!!
                           choices=[],
                           coerce=int)
    general_category = StringField('Category for video',
                                   default='',
                                   validators=[Length(min=0, max=254)])
    is_score_model = BooleanField('Score imported images')
    score_model = SelectField('Classification model', #TODO -- shall be dynamic!!!
                            choices=[(1, 'ResNet'),
                                     (2, 'EfficientNet')],
                            coerce=int)

    is_dedup = BooleanField('Check for duplicates')
    dedup_model = SelectField(
        'Model for image deduplication',
        choices=[(1, 'inception_v1',)],
        coerce=int
    )
    is_dedup_automatic = BooleanField('Automatic threshold deduplication ')
    dedup_treshold = FloatField(
        'Threshold',
        default=0.0,
        validators=[
            NumberRange(
                min=0.,
                message="Can't be negative"
            )
        ]
    )

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


class SplitForm(FlaskForm):
    train_size = FloatField(label=0.7)
    test_size = FloatField(label=0.1)
    val_size = FloatField(label=0.2)
