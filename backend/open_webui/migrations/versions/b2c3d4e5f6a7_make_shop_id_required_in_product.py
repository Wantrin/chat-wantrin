"""Make shop_id required in product table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-21 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    # Supprimer les produits sans shop_id
    op.execute("DELETE FROM product WHERE shop_id IS NULL")
    
    # Rendre shop_id non nullable
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    if dialect == "sqlite":
        # SQLite ne supporte pas ALTER COLUMN ... SET NOT NULL -> batch mode (recreate table)
        with op.batch_alter_table("product", recreate="always") as batch_op:
            batch_op.alter_column("shop_id", existing_type=sa.Text(), nullable=False)
    else:
        op.alter_column(
            "product",
            "shop_id",
            existing_type=sa.Text(),
            nullable=False,
        )


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    if dialect == "sqlite":
        with op.batch_alter_table("product", recreate="always") as batch_op:
            batch_op.alter_column("shop_id", existing_type=sa.Text(), nullable=True)
    else:
        op.alter_column(
            "product",
            "shop_id",
            existing_type=sa.Text(),
            nullable=True,
        )
