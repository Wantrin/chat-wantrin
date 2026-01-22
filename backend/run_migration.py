#!/usr/bin/env python3
"""Script to run Alembic migrations manually"""
import sys
from pathlib import Path

# Add the open_webui directory to the path
OPEN_WEBUI_DIR = Path(__file__).parent / "open_webui"
sys.path.insert(0, str(OPEN_WEBUI_DIR.parent))

from alembic import command
from alembic.config import Config

def main():
    alembic_cfg = Config(OPEN_WEBUI_DIR / "alembic.ini")
    
    # Set the script location dynamically
    migrations_path = OPEN_WEBUI_DIR / "migrations"
    alembic_cfg.set_main_option("script_location", str(migrations_path))
    
    print("Running Alembic migrations...")
    try:
        command.upgrade(alembic_cfg, "head")
        print("Migrations completed successfully!")
    except Exception as e:
        print(f"Error running migrations: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
