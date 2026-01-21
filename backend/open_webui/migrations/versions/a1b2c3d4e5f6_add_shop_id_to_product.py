"""Add shop_id to product table

Revision ID: a1b2c3d4e5f6
Revises: f5a6b7c8d9e0
Create Date: 2025-01-21 11:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("product", sa.Column("shop_id", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("product", "shop_id")
