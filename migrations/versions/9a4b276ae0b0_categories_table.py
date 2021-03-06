"""Categories table

Revision ID: 9a4b276ae0b0
Revises: 35ca87881ab5
Create Date: 2021-07-03 12:35:06.225957

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a4b276ae0b0'
down_revision = '35ca87881ab5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('version_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['version_id'], ['versions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('categories')
    # ### end Alembic commands ###
