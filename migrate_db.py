"""
Manual database migration script to add face_match_score column
Run this if auto-migration fails
"""
import os
from sqlalchemy import create_engine, text

# Get database URL from environment
database_url = os.environ.get('DATABASE_URL')

if not database_url:
    print("❌ DATABASE_URL not found in environment variables")
    exit(1)

# Fix postgres:// to postgresql:// if needed (Render uses postgres://)
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

print(f"🔗 Connecting to database...")

try:
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='sighting' AND column_name='face_match_score'
        """))
        
        if result.fetchone():
            print("✅ face_match_score column already exists")
        else:
            print("⚙️ Adding face_match_score column...")
            conn.execute(text("ALTER TABLE sighting ADD COLUMN face_match_score FLOAT"))
            conn.commit()
            print("✅ face_match_score column added successfully!")
            
except Exception as e:
    print(f"❌ Migration failed: {str(e)}")
    exit(1)

print("✅ Migration complete!")
