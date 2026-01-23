"""Add delivery tracking fields to order table

Revision ID: k1l2m3n4o5p6
Revises: h8i9j0k1l2m3
Create Date: 2025-01-23 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "k1l2m3n4o5p6"
down_revision = "j0k1l2m3n4o5"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    
    # Add delivery tracking columns to order table
    op.add_column("order", sa.Column("tracking_number", sa.Text(), nullable=True))
    op.add_column("order", sa.Column("carrier", sa.Text(), nullable=True))
    op.add_column("order", sa.Column("tracking_url", sa.Text(), nullable=True))
    op.add_column("order", sa.Column("shipped_at", sa.BigInteger(), nullable=True))
    op.add_column("order", sa.Column("estimated_delivery_date", sa.BigInteger(), nullable=True))
    op.add_column("order", sa.Column("delivered_at", sa.BigInteger(), nullable=True))
    
    # Create order_status_history table
    if dialect == "sqlite":
        op.create_table(
            "order_status_history",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("order_id", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )
    else:
        op.create_table(
            "order_status_history",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("order_id", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
        )
        # Add foreign key constraint for PostgreSQL
        op.create_foreign_key(
            "fk_order_status_history_order_id",
            "order_status_history",
            "order",
            ["order_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade():
    op.drop_table("order_status_history")
    op.drop_column("order", "delivered_at")
    op.drop_column("order", "estimated_delivery_date")
    op.drop_column("order", "shipped_at")
    op.drop_column("order", "tracking_url")
    op.drop_column("order", "carrier")
    op.drop_column("order", "tracking_number")
