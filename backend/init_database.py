#!/usr/bin/env python3
"""
Database Initialization Script for KG RAG v2.0-beta

This script initializes the PostgreSQL database schema for v2.0-beta.
It is self-contained and does not depend on external files.

Usage:
    # Initialize schema (create tables, indexes, functions)
    python3 init_database.py
    
    # Check current status
    python3 init_database.py --status
    
    # Apply migrations only
    python3 init_database.py --migrate
    
    # Reset database (DROP all tables and recreate)
    python3 init_database.py --reset
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Database configuration
DEFAULT_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'kg_rag',
    'user': 'postgres',
    'password': 'postgres'
}

# Path to schema file (local to v2.0-beta)
SCHEMA_FILE = Path(__file__).parent / "schema.sql"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def get_connection(config: dict = None):
    """Get database connection."""
    import asyncpg
    cfg = config or DEFAULT_CONFIG
    return await asyncpg.connect(
        host=cfg['host'],
        port=cfg['port'],
        database=cfg['database'],
        user=cfg['user'],
        password=cfg['password']
    )


async def check_database_exists(config: dict = None) -> bool:
    """Check if database exists."""
    import asyncpg
    cfg = config or DEFAULT_CONFIG
    try:
        conn = await asyncpg.connect(
            host=cfg['host'],
            port=cfg['port'],
            database=cfg['database'],
            user=cfg['user'],
            password=cfg['password']
        )
        await conn.close()
        return True
    except asyncpg.InvalidCatalogNameError:
        return False
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False


async def create_database(config: dict = None):
    """Create database if it doesn't exist."""
    import asyncpg
    cfg = config or DEFAULT_CONFIG
    
    try:
        # Connect to default 'postgres' database to create new one
        conn = await asyncpg.connect(
            host=cfg['host'],
            port=cfg['port'],
            database='postgres',
            user=cfg['user'],
            password=cfg['password']
        )
        
        # Check if database exists
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            cfg['database']
        )
        
        if not result:
            print(f"📦 Creating database '{cfg['database']}'...")
            await conn.execute(f"CREATE DATABASE {cfg['database']}")
            print(f"✅ Database '{cfg['database']}' created")
        else:
            print(f"📦 Database '{cfg['database']}' already exists")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to create database: {e}")
        return False


async def init_schema(config: dict = None, force: bool = False):
    """Initialize database schema from schema.sql."""
    
    if not SCHEMA_FILE.exists():
        print(f"❌ Schema file not found: {SCHEMA_FILE}")
        return False
    
    print(f"📄 Reading schema from: {SCHEMA_FILE}")
    
    with open(SCHEMA_FILE, 'r') as f:
        schema_sql = f.read()
    
    conn = await get_connection(config)
    
    try:
        # Check if schema already exists
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        existing_tables = {t['table_name'] for t in tables}
        
        if 'entities' in existing_tables and not force:
            print("⚠️  Schema already initialized (entities table exists)")
            print("   Use --force to re-initialize or --reset to drop and recreate")
            return True
        
        print("🔧 Applying schema...")
        
        # Split and execute statements
        statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
        
        for i, statement in enumerate(statements, 1):
            if not statement or statement.startswith('--'):
                continue
            
            try:
                await conn.execute(statement)
                print(f"   ✓ Statement {i}/{len(statements)}")
            except Exception as e:
                # Ignore "already exists" errors
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"   ⚠ Statement {i} (already exists)")
                else:
                    print(f"   ❌ Statement {i} failed: {e}")
                    raise
        
        print("✅ Schema initialized successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Schema initialization failed: {e}")
        return False
        
    finally:
        await conn.close()


async def apply_migrations(config: dict = None):
    """Apply pending migrations."""
    
    if not MIGRATIONS_DIR.exists():
        print(f"⚠️  Migrations directory not found: {MIGRATIONS_DIR}")
        return True
    
    print("📂 Applying migrations...")
    
    # Get all .sql migration files
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    
    if not migration_files:
        print("   No migrations found")
        return True
    
    conn = await get_connection(config)
    
    try:
        # Create migrations tracking table if not exists
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _schema_migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Get applied migrations
        applied = await conn.fetch("SELECT filename FROM _schema_migrations")
        applied_files = {row['filename'] for row in applied}
        
        for migration_file in migration_files:
            if migration_file.name in applied_files:
                print(f"   ⏭️  {migration_file.name} (already applied)")
                continue
            
            print(f"   📝 Applying {migration_file.name}...")
            
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            
            statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
            
            async with conn.transaction():
                for statement in statements:
                    if statement and not statement.startswith('--'):
                        await conn.execute(statement)
                
                # Record migration
                await conn.execute(
                    "INSERT INTO _schema_migrations (filename) VALUES ($1)",
                    migration_file.name
                )
            
            print(f"   ✅ {migration_file.name} applied")
        
        print("✅ All migrations applied!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
        
    finally:
        await conn.close()


async def reset_database(config: dict = None):
    """Drop all tables and recreate schema."""
    
    print("⚠️  WARNING: This will DELETE ALL DATA in the database!")
    confirm = input("Type 'yes' to confirm: ")
    
    if confirm.lower() != 'yes':
        print("❌ Reset cancelled")
        return False
    
    conn = await get_connection(config)
    
    try:
        print("🗑️  Dropping existing tables...")
        
        # Drop tables in correct order (respecting foreign keys)
        tables = ['chunks', 'relationships', 'entities', '_schema_migrations']
        
        for table in tables:
            try:
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"   🗑️  Dropped {table}")
            except Exception as e:
                print(f"   ⚠️  Could not drop {table}: {e}")
        
        print("✅ All tables dropped")
        
        # Reinitialize schema
        return await init_schema(config, force=True)
        
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return False
        
    finally:
        await conn.close()


async def show_status(config: dict = None):
    """Show database status."""
    
    print("\n📊 Database Status")
    print("=" * 50)
    
    # Check if database exists
    if not await check_database_exists(config):
        print("❌ Database does not exist")
        return
    
    conn = await get_connection(config)
    
    try:
        # Check tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        if not tables:
            print("⚠️  No tables found - schema not initialized")
            return
        
        print(f"\n📋 Tables ({len(tables)}):")
        for table in tables:
            table_name = table['table_name']
            
            # Get row count
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                print(f"   • {table_name}: {count:,} rows")
            except:
                print(f"   • {table_name}")
        
        # Check migrations
        try:
            migrations = await conn.fetch(
                "SELECT filename, applied_at FROM _schema_migrations ORDER BY applied_at"
            )
            if migrations:
                print(f"\n📂 Applied Migrations ({len(migrations)}):")
                for mig in migrations:
                    print(f"   • {mig['filename']} ({mig['applied_at'].strftime('%Y-%m-%d %H:%M')})")
        except:
            pass
        
        # Check extensions
        extensions = await conn.fetch(
            "SELECT extname FROM pg_extension WHERE extname IN ('vector')"
        )
        if extensions:
            print(f"\n🔌 Extensions: {', '.join(e['extname'] for e in extensions)}")
        
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        
    finally:
        await conn.close()


async def verify_setup(config: dict = None):
    """Verify database setup is complete."""
    
    print("🔍 Verifying database setup...")
    
    checks = {
        'database_exists': False,
        'schema_initialized': False,
        'entities_table': False,
        'relationships_table': False,
        'chunks_table': False,
        'vector_extension': False
    }
    
    # Check database
    checks['database_exists'] = await check_database_exists(config)
    if not checks['database_exists']:
        print("❌ Database does not exist")
        return checks
    
    conn = await get_connection(config)
    
    try:
        # Check tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_names = {t['table_name'] for t in tables}
        
        checks['entities_table'] = 'entities' in table_names
        checks['relationships_table'] = 'relationships' in table_names
        checks['chunks_table'] = 'chunks' in table_names
        checks['schema_initialized'] = checks['entities_table']
        
        # Check vector extension
        try:
            result = await conn.fetchval(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            )
            checks['vector_extension'] = result is not None
        except:
            pass
        
        # Print results
        all_good = all(checks.values())
        
        for check, status in checks.items():
            icon = "✅" if status else "❌"
            print(f"   {icon} {check.replace('_', ' ').title()}")
        
        if all_good:
            print("\n✅ Database setup is complete!")
        else:
            print("\n⚠️  Database setup is incomplete")
            print("   Run: python3 init_database.py")
        
        return checks
        
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Initialize KG RAG v2.0-beta database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize everything (create DB, schema, migrations)
  python3 init_database.py
  
  # Check current status
  python3 init_database.py --status
  
  # Verify setup
  python3 init_database.py --verify
  
  # Apply migrations only
  python3 init_database.py --migrate
  
  # Reset everything (DANGER: deletes all data)
  python3 init_database.py --reset
  
  # Force re-initialize schema
  python3 init_database.py --force
        """
    )
    
    parser.add_argument('--status', action='store_true',
                        help='Show database status')
    parser.add_argument('--verify', action='store_true',
                        help='Verify database setup')
    parser.add_argument('--migrate', action='store_true',
                        help='Apply migrations only')
    parser.add_argument('--reset', action='store_true',
                        help='Reset database (DANGER: deletes all data)')
    parser.add_argument('--force', action='store_true',
                        help='Force re-initialize schema')
    parser.add_argument('--host', default='localhost',
                        help='PostgreSQL host (default: localhost)')
    parser.add_argument('--port', type=int, default=5432,
                        help='PostgreSQL port (default: 5432)')
    parser.add_argument('--database', default='kg_rag',
                        help='Database name (default: kg_rag)')
    parser.add_argument('--user', default='postgres',
                        help='PostgreSQL user (default: postgres)')
    parser.add_argument('--password', default='postgres',
                        help='PostgreSQL password (default: postgres)')
    
    args = parser.parse_args()
    
    config = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password
    }
    
    if args.status:
        asyncio.run(show_status(config))
        return
    
    if args.verify:
        asyncio.run(verify_setup(config))
        return
    
    if args.reset:
        asyncio.run(reset_database(config))
        return
    
    if args.migrate:
        asyncio.run(apply_migrations(config))
        return
    
    # Default: full initialization
    print("=" * 60)
    print("KG RAG v2.0-beta Database Initialization")
    print("=" * 60)
    
    # Create database if needed
    if not asyncio.run(create_database(config)):
        print("❌ Failed to create database")
        sys.exit(1)
    
    # Initialize schema
    if not asyncio.run(init_schema(config, force=args.force)):
        print("❌ Failed to initialize schema")
        sys.exit(1)
    
    # Apply migrations
    if not asyncio.run(apply_migrations(config)):
        print("❌ Failed to apply migrations")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Database initialization complete!")
    print("=" * 60)
    
    # Show status
    asyncio.run(show_status(config))


if __name__ == "__main__":
    main()
