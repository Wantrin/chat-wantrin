"""add_is_public_to_shop

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2025-01-23 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'm3n4o5p6q7r8'
down_revision = 'l2m3n4o5p6q7'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_public column to shop table
    op.add_column('shop', sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    # Remove is_public column from shop table
    op.drop_column('shop', 'is_public')
