"""Add VersionChildren for multiple versions children

Revision ID: 35ca87881ab5
Revises: 624ef6e768e3
Create Date: 2021-07-03 07:08:11.523044

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '35ca87881ab5'
down_revision = '624ef6e768e3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('version_children',
    sa.Column('child_id', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['child_id'], ['versions.id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['versions.id'], )
    )
    op.create_foreign_key(None, 'versions', 'users', ['user_id'], ['id'])
    
    op.execute("insert into version_children (child_id, parent_id) select child_id, id as parent_id from versions where child_id is not null")
    
    op.drop_column('versions', 'child_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('versions', sa.Column('child_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'versions', type_='foreignkey')
    op.drop_table('version_children')
    # ### end Alembic commands ###
