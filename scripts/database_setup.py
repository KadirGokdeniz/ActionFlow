#!/usr/bin/env python3
"""
ActionFlow AI - Database Initialization Script
"""

import subprocess
import sys
import time
import argparse

# ✅ EKLENDİ
from dotenv import load_dotenv
load_dotenv()

# ═══════════════════════════════════════════════════════════════════
# DOCKER SETUP
# ═══════════════════════════════════════════════════════════════════

DOCKER_CONFIG = {
    "container_name": "actionflow-db",
    "image": "pgvector/pgvector:pg16",
    "user": "actionflow",
    "password": "dev123",
    "database": "actionflow",
    "port": 5432
}


def start_postgres_docker():
    """Start PostgreSQL container with pgvector"""

    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={DOCKER_CONFIG['container_name']}", "--format", "{{.Names}}"],
        capture_output=True, text=True
    )

    if DOCKER_CONFIG['container_name'] in result.stdout:
        print(f"Container '{DOCKER_CONFIG['container_name']}' already exists.")

        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={DOCKER_CONFIG['container_name']}", "--format", "{{.Names}}"],
            capture_output=True, text=True
        )

        if DOCKER_CONFIG['container_name'] not in result.stdout:
            print("Starting existing container...")
            subprocess.run(["docker", "start", DOCKER_CONFIG['container_name']], check=True)
        else:
            print("Container is already running.")
        return

    print("Creating new PostgreSQL container with pgvector...")

    cmd = [
        "docker", "run", "-d",
        "--name", DOCKER_CONFIG['container_name'],
        "-e", f"POSTGRES_USER={DOCKER_CONFIG['user']}",
        "-e", f"POSTGRES_PASSWORD={DOCKER_CONFIG['password']}",
        "-e", f"POSTGRES_DB={DOCKER_CONFIG['database']}",
        "-p", f"{DOCKER_CONFIG['port']}:5432",
        "-v", "actionflow-pgdata:/var/lib/postgresql/data",
        DOCKER_CONFIG['image']
    ]

    subprocess.run(cmd, check=True)
    print("Container started. Waiting for PostgreSQL to be ready...")

    for i in range(30):
        result = subprocess.run(
            ["docker", "exec", DOCKER_CONFIG['container_name'],
             "pg_isready", "-U", DOCKER_CONFIG['user']],
            capture_output=True
        )
        if result.returncode == 0:
            print("PostgreSQL is ready!")
            return
        time.sleep(1)
        print(f"Waiting... ({i+1}/30)")

    raise Exception("PostgreSQL failed to start within 30 seconds")


# ═══════════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ═══════════════════════════════════════════════════════════════════

def init_database():
    """Initialize database schema using SQLAlchemy"""

    try:
        from pathlib import Path
        backend_path = Path(__file__).resolve().parents[1] / "backend"
        sys.path.insert(0, str(backend_path))

        from sqlalchemy import create_engine, text
        from app.core.database import Base, SYNC_DATABASE_URL
    except ImportError as e:
        print("Missing dependencies. Install with:")
        print("  pip install sqlalchemy psycopg2-binary pgvector")
        print(f"Error: {e}")
        sys.exit(1)

    print("\nConnecting to database...")
    print("URL:", SYNC_DATABASE_URL)

    # ✅ HARDCODE KALDIRILDI
    engine = create_engine(SYNC_DATABASE_URL)

    with engine.connect() as conn:
        print("Creating pgvector extension...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    print("Creating tables...")
    Base.metadata.create_all(engine)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]

    print("\n✓ Database initialized successfully!")
    print(f"  Tables created: {', '.join(tables)}")

    return tables


def seed_sample_policies():
    """Add sample policies for testing RAG"""

    from pathlib import Path
    backend__path = Path(__file__).parent.parent / "backend" / "app"
    sys.path.insert(0, str(backend__path))

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.database import SYNC_DATABASE_URL
    import uuid

    # ✅ HARDCODE KALDIRILDI
    engine = create_engine(SYNC_DATABASE_URL)

    sample_policies = [
        {
            "id": str(uuid.uuid4()),
            "category": "cancellation",
            "provider": "general",
            "title": "Standard Hotel Cancellation Policy",
            "content": "Hotels can be cancelled free of charge up to 24 hours before check-in."
        }
    ]

    with Session(engine) as session:
        existing = session.query(Policy).count()
        if existing > 0:
            print(f"  Policies already seeded ({existing} records)")
            return

        for policy_data in sample_policies:
            policy = Policy(**policy_data)
            session.add(policy)

        session.commit()
        print(f"  ✓ Seeded {len(sample_policies)} sample policies")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Initialize ActionFlow database")
    parser.add_argument("--docker", action="store_true", help="Start Docker container automatically")
    parser.add_argument("--seed", action="store_true", help="Seed sample data")
    args = parser.parse_args()

    print("=" * 60)
    print("ActionFlow AI - Database Initialization")
    print("=" * 60)

    if args.docker:
        start_postgres_docker()
        time.sleep(2)

    tables = init_database()

    if args.seed:
        print("\nSeeding sample data...")
        seed_sample_policies()

    print("\n" + "=" * 60)
    print("Connection string for .env:")
    print("DATABASE_URL=postgresql+asyncpg://actionflow:dev123@host.docker.internal:5432/actionflow")
    print("=" * 60)


if __name__ == "__main__":
    main()
