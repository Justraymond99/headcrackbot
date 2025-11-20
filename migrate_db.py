"""Database migration script to add new columns."""
import sqlite3
from pathlib import Path
from config import DATABASE_URL

def migrate_database():
    """Add new columns to existing database."""
    # Extract database path from SQLAlchemy URL
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        if db_path.startswith("./"):
            db_path = Path(__file__).parent / db_path[2:]
        else:
            db_path = Path(db_path)
    else:
        print("This migration script only works with SQLite databases")
        return
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("Run 'python main.py init' to create a new database")
        return
    
    print(f"Migrating database at {db_path}...")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(games)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add fighter1 and fighter2 columns if they don't exist
        if 'fighter1' not in columns:
            print("Adding fighter1 column...")
            cursor.execute("ALTER TABLE games ADD COLUMN fighter1 VARCHAR")
        
        if 'fighter2' not in columns:
            print("Adding fighter2 column...")
            cursor.execute("ALTER TABLE games ADD COLUMN fighter2 VARCHAR")
        
        # Check player_props table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_props'")
        if not cursor.fetchone():
            print("Creating player_props table...")
            cursor.execute("""
                CREATE TABLE player_props (
                    id INTEGER PRIMARY KEY,
                    game_id INTEGER,
                    player_name VARCHAR NOT NULL,
                    prop_type VARCHAR NOT NULL,
                    prop_value FLOAT,
                    over_odds FLOAT,
                    under_odds FLOAT,
                    yes_odds FLOAT,
                    no_odds FLOAT,
                    market_key VARCHAR,
                    description VARCHAR,
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY(game_id) REFERENCES games (id)
                )
            """)
        else:
            # Check player_props columns
            cursor.execute("PRAGMA table_info(player_props)")
            prop_columns = [row[1] for row in cursor.fetchall()]
            
            if 'yes_odds' not in prop_columns:
                print("Adding yes_odds column to player_props...")
                cursor.execute("ALTER TABLE player_props ADD COLUMN yes_odds FLOAT")
            
            if 'no_odds' not in prop_columns:
                print("Adding no_odds column to player_props...")
                cursor.execute("ALTER TABLE player_props ADD COLUMN no_odds FLOAT")
            
            if 'market_key' not in prop_columns:
                print("Adding market_key column to player_props...")
                cursor.execute("ALTER TABLE player_props ADD COLUMN market_key VARCHAR")
            
            if 'description' not in prop_columns:
                print("Adding description column to player_props...")
                cursor.execute("ALTER TABLE player_props ADD COLUMN description VARCHAR")
        
        # Check legs table
        cursor.execute("PRAGMA table_info(legs)")
        leg_columns = [row[1] for row in cursor.fetchall()]
        
        if 'player_prop_id' not in leg_columns:
            print("Adding player_prop_id column to legs...")
            cursor.execute("ALTER TABLE legs ADD COLUMN player_prop_id INTEGER")
        
        if 'prop_type' not in leg_columns:
            print("Adding prop_type column to legs...")
            cursor.execute("ALTER TABLE legs ADD COLUMN prop_type VARCHAR")
        
        if 'prop_value' not in leg_columns:
            print("Adding prop_value column to legs...")
            cursor.execute("ALTER TABLE legs ADD COLUMN prop_value FLOAT")
        
        if 'player_name' not in leg_columns:
            print("Adding player_name column to legs...")
            cursor.execute("ALTER TABLE legs ADD COLUMN player_name VARCHAR")
        
        conn.commit()
        print("✅ Database migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()

