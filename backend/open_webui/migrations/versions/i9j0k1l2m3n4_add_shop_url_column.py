"""Add url column to shop table

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2025-01-21 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
import re

revision = "i9j0k1l2m3n4"
down_revision = "h8i9j0k1l2m3"
branch_labels = None
depends_on = None


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a shop name."""
    if not name:
        return ""
    slug = name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    slug = slug.strip('-')
    return slug


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    
    # Check if the column already exists
    inspector = Inspector.from_engine(bind)
    columns = [col["name"] for col in inspector.get_columns("shop")]
    
    # Add the url column only if it doesn't exist
    if "url" not in columns:
        op.add_column("shop", sa.Column("url", sa.Text(), nullable=True))
    
    # Create unique index on url column
    try:
        # Check if index already exists
        indexes = [idx["name"] for idx in inspector.get_indexes("shop")]
        if "ix_shop_url" not in indexes:
            op.create_index("ix_shop_url", "shop", ["url"], unique=True)
    except Exception:
        # Index might already exist or database doesn't support it
        pass
    
    # Generate URLs for existing shops based on their names
    connection = op.get_bind()
    
    # Get all shops
    shops = connection.execute(
        sa.text("SELECT id, name FROM shop WHERE url IS NULL")
    ).fetchall()
    
    # Generate unique URLs for each shop
    for shop_id, shop_name in shops:
        base_slug = generate_slug(shop_name) if shop_name else f"shop-{shop_id[:8]}"
        slug = base_slug
        counter = 1
        
        # Make sure the slug is unique
        while True:
            existing = connection.execute(
                sa.text("SELECT id FROM shop WHERE url = :url"),
                {"url": slug}
            ).fetchone()
            if not existing:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Update the shop with the generated URL
        connection.execute(
            sa.text("UPDATE shop SET url = :url WHERE id = :id"),
            {"url": slug, "id": shop_id}
        )
    
    connection.commit()


def downgrade():
    # Drop the unique index
    try:
        op.drop_index("ix_shop_url", table_name="shop")
    except Exception:
        pass
    
    # Drop the url column
    op.drop_column("shop", "url")
