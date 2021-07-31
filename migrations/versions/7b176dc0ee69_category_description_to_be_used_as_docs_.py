"""Category description to be used as docs/requirements
Revision ID: 7b176dc0ee69
Revises: a2c5ed6d633c
Create Date: 2021-07-19 12:05:34.966342
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b176dc0ee69'
down_revision = 'a2c5ed6d633c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('categories', sa.Column('description', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('categories', 'description')
    # ### end Alembic commands ###