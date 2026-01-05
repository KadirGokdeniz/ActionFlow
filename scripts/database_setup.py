#!/usr/bin/env python3
"""
ActionFlow AI - Database Initialization Script

Usage:
    1. Start PostgreSQL: docker run -d --name actionflow-db ...
    2. Run this script: python init_db.py

Or use: ./init_db.py --docker  (starts container automatically)
"""

import subprocess
import sys
import time
import argparse

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
    
    # Check if container exists
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={DOCKER_CONFIG['container_name']}", "--format", "{{.Names}}"],
        capture_output=True, text=True
    )
    
    if DOCKER_CONFIG['container_name'] in result.stdout:
        print(f"Container '{DOCKER_CONFIG['container_name']}' already exists.")
        
        # Check if running
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
        "-v", "actionflow-pgdata:/var/lib/postgresql/data",  # Persistent volume
        DOCKER_CONFIG['image']
    ]
    
    subprocess.run(cmd, check=True)
    print("Container started. Waiting for PostgreSQL to be ready...")
    
    # Wait for PostgreSQL to be ready
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
    
    # Import here to avoid issues if dependencies not installed
    try:
        from pathlib import Path
        import sys
        # Backend klasöründen import et
        backend_path = Path(__file__).parent.parent / "backend"
        sys.path.insert(0, str(backend_path))
        
        from sqlalchemy import create_engine, text
        from database import Base, SYNC_DATABASE_URL
    except ImportError as e:
        print(f"Missing dependencies. Install with:")
        print(f"  pip install sqlalchemy psycopg2-binary pgvector")
        print(f"Error: {e}")
        sys.exit(1)
    
    print(f"\nConnecting to database...")
    # Mask password for display
    display_url = SYNC_DATABASE_URL
    if ":" in display_url and "@" in display_url:
        start = display_url.index(":", display_url.index("://") + 3)
        end = display_url.index("@")
        display_url = display_url[:start+1] + "****" + display_url[end:]
    print(f"URL: {display_url}")
    
    engine = create_engine(SYNC_DATABASE_URL)
    
    # Create pgvector extension
    with engine.connect() as conn:
        print("Creating pgvector extension...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    
    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(engine)
    
    # Verify tables
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
    
    print(f"\n✓ Database initialized successfully!")
    print(f"  Tables created: {', '.join(tables)}")
    
    return tables


def seed_sample_policies():
    """Add sample policies for testing RAG"""
    
    from pathlib import Path
    import sys
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from database import Base, Policy, SYNC_DATABASE_URL
    import uuid
    
    engine = create_engine(SYNC_DATABASE_URL.replace("+asyncpg", ""))
    
    sample_policies = [
        {
            "id": str(uuid.uuid4()),
            "category": "cancellation",
            "provider": "general",
            "title": "Standard Hotel Cancellation Policy",
            "content": """Hotels can be cancelled free of charge up to 24 hours before check-in. 
            Cancellations made within 24 hours of check-in will be charged one night's stay. 
            No-shows will be charged the full booking amount. Refunds are processed within 3-5 business days."""
        },
        {
            "id": str(uuid.uuid4()),
            "category": "cancellation",
            "provider": "general",
            "title": "Flight Cancellation Policy",
            "content": """Flight cancellations are subject to airline policies. Most economy tickets are non-refundable 
            but may be changed for a fee. Premium and business class tickets typically offer free cancellation 
            up to 24 hours before departure. Refunds for eligible tickets are processed within 7-14 business days."""
        },
        {
            "id": str(uuid.uuid4()),
            "category": "refund",
            "provider": "general",
            "title": "Refund Processing Times",
            "content": """Refunds are processed based on the original payment method. Credit card refunds take 3-5 
            business days. Bank transfers take 5-7 business days. The refund amount will be the original booking 
            amount minus any applicable cancellation fees."""
        },
        {
            "id": str(uuid.uuid4()),
            "category": "baggage",
            "provider": "Turkish Airlines",
            "title": "Turkish Airlines Baggage Allowance",
            "content": """Economy class: 23kg checked baggage, 8kg cabin baggage. Business class: 32kg checked baggage, 
            8kg cabin baggage. Excess baggage fees apply for overweight or additional pieces. Sports equipment 
            may require special handling and fees."""
        },
        {
            "id": str(uuid.uuid4()),
            "category": "check-in",
            "provider": "general",
            "title": "Online Check-in Guidelines",
            "content": """Online check-in opens 24-48 hours before departure depending on the airline. 
            You will need your booking reference (PNR) and passport details. After check-in, download 
            your boarding pass or save it to your mobile wallet. Arrive at the airport at least 2 hours 
            before domestic flights and 3 hours before international flights."""
        }
    ]
    
    with Session(engine) as session:
        # Check if policies already exist
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
        time.sleep(2)  # Give it a moment
    
    tables = init_database()
    
    if args.seed:
        print("\nSeeding sample data...")
        seed_sample_policies()
    
    print("\n" + "=" * 60)
    print("Connection string for .env:")
    print(f"DATABASE_URL=postgresql+asyncpg://{DOCKER_CONFIG['user']}:{DOCKER_CONFIG['password']}@localhost:{DOCKER_CONFIG['port']}/{DOCKER_CONFIG['database']}")
    print("=" * 60)


if __name__ == "__main__":
    main()