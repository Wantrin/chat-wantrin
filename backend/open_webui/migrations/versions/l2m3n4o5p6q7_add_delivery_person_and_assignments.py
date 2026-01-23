"""Add delivery person table and assignment fields to order

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2025-01-23 14:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "l2m3n4o5p6q7"
down_revision = "k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    
    # Add assignment columns to order table
    op.add_column("order", sa.Column("assigned_user_id", sa.Text(), nullable=True))
    op.add_column("order", sa.Column("assigned_delivery_person_id", sa.Text(), nullable=True))
    
    # Create delivery_person table
    if dialect == "sqlite":
        op.create_table(
            "delivery_person",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("shop_id", sa.Text(), nullable=False),
            sa.Column("user_id", sa.Text(), nullable=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("email", sa.Text(), nullable=True),
            sa.Column("phone", sa.Text(), nullable=True),
            sa.Column("vehicle_type", sa.Text(), nullable=True),
            sa.Column("vehicle_plate", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("meta", sa.Text(), nullable=True),  # JSON stored as TEXT in SQLite
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
        )
    else:
        op.create_table(
            "delivery_person",
            sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
            sa.Column("shop_id", sa.Text(), nullable=False),
            sa.Column("user_id", sa.Text(), nullable=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("email", sa.Text(), nullable=True),
            sa.Column("phone", sa.Text(), nullable=True),
            sa.Column("vehicle_type", sa.Text(), nullable=True),
            sa.Column("vehicle_plate", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
        )
        # Add foreign key constraints for PostgreSQL
        op.create_foreign_key(
            "fk_delivery_person_shop_id",
            "delivery_person",
            "shop",
            ["shop_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade():
    op.drop_table("delivery_person")
    op.drop_column("order", "assigned_delivery_person_id")
    op.drop_column("order", "assigned_user_id")
