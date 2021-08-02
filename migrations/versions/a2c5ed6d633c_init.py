"""Init
Revision ID: a2c5ed6d633c
Revises:
Create Date: 2021-07-19 11:54:38.041158
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2c5ed6d633c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('data_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('path', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('path')
    )
    op.create_table('moderation',
    sa.Column('src', sa.String(), nullable=False),
    sa.Column('file', sa.String(), nullable=False),
    sa.Column('src_media_type', sa.String(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('src', 'file')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('_password', sa.Binary(), nullable=False),
    sa.Column('authenticated', sa.Boolean(), nullable=True),
    sa.Column('email_confirmation_sent_on', sa.DateTime(), nullable=True),
    sa.Column('email_confirmed', sa.Boolean(), nullable=True),
    sa.Column('email_confirmed_on', sa.DateTime(), nullable=True),
    sa.Column('registered_on', sa.DateTime(), nullable=True),
    sa.Column('last_logged_in', sa.DateTime(), nullable=True),
    sa.Column('current_logged_in', sa.DateTime(), nullable=True),
    sa.Column('role', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('status', sa.SmallInteger(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('version_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('task', sa.SmallInteger(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['version_id'], ['versions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('todo_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('version_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('file_path', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('audio_text', sa.String(), nullable=True),
    sa.Column('gt_category', sa.String(), nullable=False),
    sa.Column('assigned_categories_json', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['version_id'], ['versions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('file_path')
    )
    op.create_table('version_children',
    sa.Column('child_id', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['child_id'], ['versions.id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['versions.id'], ),
    sa.PrimaryKeyConstraint('child_id', 'parent_id')
    )
    op.create_table('tmp_table',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('node_name', sa.String(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
    sa.ForeignKeyConstraint(['item_id'], ['data_items.id'], ),
    sa.ForeignKeyConstraint(['node_name'], ['versions.name'], ),
    sa.PrimaryKeyConstraint('item_id', 'node_name')
    )
    op.create_table('version_items',
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('version_id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
    sa.ForeignKeyConstraint(['item_id'], ['data_items.id'], ),
    sa.ForeignKeyConstraint(['version_id'], ['versions.id'], ),
    sa.PrimaryKeyConstraint('item_id', 'version_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('version_items')
    op.drop_table('tmp_table')
    op.drop_table('version_children')
    op.drop_table('todo_items')
    op.drop_table('categories')
    op.drop_table('versions')
    op.drop_table('users')
    op.drop_table('moderation')
    op.drop_table('data_items')
    # ### end Alembic commands ###
