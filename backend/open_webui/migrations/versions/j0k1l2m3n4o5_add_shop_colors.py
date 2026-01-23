"""Add primary_color and secondary_color columns to shop table

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2025-01-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "j0k1l2m3n4o5"
down_revision = "i9j0k1l2m3n4"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    
    # Check if the columns already exist
    inspector = Inspector.from_engine(bind)
    columns = [col["name"] for col in inspector.get_columns("shop")]
    
    # Add primary_color column only if it doesn't exist
    if "primary_color" not in columns:
        op.add_column("shop", sa.Column("primary_color", sa.Text(), nullable=True))
    
    # Add secondary_color column only if it doesn't exist
    if "secondary_color" not in columns:
        op.add_column("shop", sa.Column("secondary_color", sa.Text(), nullable=True))


def downgrade():
    # Drop the columns
    try:
        op.drop_column("shop", "secondary_color")
    except Exception:
        pass
    
    try:
        op.drop_column("shop", "primary_color")
    except Exception:
        pass
