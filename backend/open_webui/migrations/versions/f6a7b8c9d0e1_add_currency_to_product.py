"""Add currency column to product table

Revision ID: f6a7b8c9d0e1
Revises: c3d4e5f6a7b8
Create Date: 2025-01-22 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("product", sa.Column("currency", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("product", "currency")
