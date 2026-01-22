#!/usr/bin/env python3
"""Script to create the order table directly in the database"""
import sys
from pathlib import Path

# Add the open_webui directory to the path
OPEN_WEBUI_DIR = Path(__file__).parent / "open_webui"
sys.path.insert(0, str(OPEN_WEBUI_DIR.parent))

from open_webui.env import DATABASE_URL
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def create_order_table():
    """Create the order table directly"""
    engine = create_engine(DATABASE_URL)
    
    # Check if table already exists
    with engine.connect() as conn:
        inspector = __import__('sqlalchemy').inspect(engine)
        if 'order' in inspector.get_table_names():
            print("Table 'order' already exists. Skipping creation.")
            return
    
    # Create table SQL
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS "order" (
        id TEXT PRIMARY KEY UNIQUE NOT NULL,
        user_id TEXT,
        shop_id TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        customer_phone TEXT,
        shipping_address TEXT NOT NULL,
        items TEXT NOT NULL,
        subtotal REAL NOT NULL,
        shipping_cost REAL DEFAULT 0.0,
        total REAL NOT NULL,
        currency TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        notes TEXT,
        meta TEXT,
        created_at INTEGER,
        updated_at INTEGER
    );
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
        print("Table 'order' created successfully!")
    except Exception as e:
        print(f"Error creating table: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_order_table()
