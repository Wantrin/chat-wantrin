"""Add order table

Revision ID: h8i9j0k1l2m3
Revises: a1b2c3d4e5f7
Create Date: 2025-01-21 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "h8i9j0k1l2m3"
down_revision = "a1b2c3d4e5f7"  # Points to task_item migration
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    
    if dialect == "sqlite":
        # SQLite doesn't support some JSON operations, use TEXT
        op.create_table(
            "order",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("user_id", sa.Text(), nullable=True),
            sa.Column("shop_id", sa.Text(), nullable=False),
            sa.Column("customer_name", sa.Text(), nullable=False),
            sa.Column("customer_email", sa.Text(), nullable=False),
            sa.Column("customer_phone", sa.Text(), nullable=True),
            sa.Column("shipping_address", sa.Text(), nullable=False),  # JSON stored as TEXT in SQLite
            sa.Column("items", sa.Text(), nullable=False),  # JSON stored as TEXT in SQLite
            sa.Column("subtotal", sa.Float(), nullable=False),
            sa.Column("shipping_cost", sa.Float(), nullable=True, default=0.0),
            sa.Column("total", sa.Float(), nullable=False),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=True, default="pending"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("meta", sa.Text(), nullable=True),  # JSON stored as TEXT in SQLite
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
        )
    else:
        # PostgreSQL and other databases support JSON natively
        op.create_table(
            "order",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("user_id", sa.Text(), nullable=True),
            sa.Column("shop_id", sa.Text(), nullable=False),
            sa.Column("customer_name", sa.Text(), nullable=False),
            sa.Column("customer_email", sa.Text(), nullable=False),
            sa.Column("customer_phone", sa.Text(), nullable=True),
            sa.Column("shipping_address", sa.JSON(), nullable=False),
            sa.Column("items", sa.JSON(), nullable=False),
            sa.Column("subtotal", sa.Float(), nullable=False),
            sa.Column("shipping_cost", sa.Float(), nullable=True, default=0.0),
            sa.Column("total", sa.Float(), nullable=False),
            sa.Column("currency", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=True, default="pending"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
        )


def downgrade():
    op.drop_table("order")
