"""Add position field to categories

Revision ID: 4f4eb99dc145
Revises: 9e1419a9055b
Create Date: 2021-07-07 11:47:32.150413

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f4eb99dc145'
down_revision = '9e1419a9055b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('categories', sa.Column('position', sa.Integer(), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('categories', 'position')
    # ### end Alembic commands ###