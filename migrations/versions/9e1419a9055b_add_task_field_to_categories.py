"""Add task field to categories

Revision ID: 9e1419a9055b
Revises: 9a4b276ae0b0
Create Date: 2021-07-07 11:36:39.688390

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e1419a9055b'
down_revision = '9a4b276ae0b0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('categories', sa.Column('task', sa.SmallInteger(), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('categories', 'task')
    # ### end Alembic commands ###