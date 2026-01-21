"""Add image_urls to product table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-21 12:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
import json

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("product", sa.Column("image_urls", sa.JSON(), nullable=True))

    # Backfill: if legacy image_url exists, set image_urls = [image_url]
    # SQLite JSON is stored as TEXT; we can safely store a JSON string.
    try:
        bind = op.get_bind()
        dialect = bind.dialect.name
        if dialect == "sqlite":
            op.execute(
                "UPDATE product SET image_urls = json_array(image_url) "
                "WHERE image_url IS NOT NULL AND (image_urls IS NULL OR image_urls = 'null')"
            )
        else:
            # Generic fallback: set to JSON text
            rows = bind.execute(sa.text("SELECT id, image_url FROM product WHERE image_url IS NOT NULL")).fetchall()
            for pid, url in rows:
                bind.execute(
                    sa.text("UPDATE product SET image_urls = :v WHERE id = :id"),
                    {"v": json.dumps([url]), "id": pid},
                )
    except Exception:
        # Don't fail migration if backfill isn't supported on a given dialect.
        pass


def downgrade():
    op.drop_column("product", "image_urls")

