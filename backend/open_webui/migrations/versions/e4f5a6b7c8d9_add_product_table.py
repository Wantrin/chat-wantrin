"""Add product table

Revision ID: e4f5a6b7c8d9
Revises: c440947495f3
Create Date: 2025-01-20 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "e4f5a6b7c8d9"
down_revision = "c440947495f3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("stock", sa.BigInteger(), nullable=True, default=0),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("access_control", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
    )


def downgrade():
    op.drop_table("product")
