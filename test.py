import sys
from sqlalchemy import text
from app.db.database import engine
from app.db.redis import redis_client

# Force UTF-8 stdout if possible on Windows
if sys.stdout.encoding != 'utf-8' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def verify_connections():
    print("=== QueueCTL Connection Verification ===")
    
    # 1. Test PostgreSQL connection
    db_ok = False
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();")).scalar()
            print(f"[PostgreSQL] Connected via {engine}")
            print(f"  Version: {result.split(',')[0] if result else 'Unknown'}")
            db_ok = True
    except Exception as e:
        print(f"[PostgreSQL] [FAILED] Connection error: {e}")

    # 2. Test Redis connection
    redis_ok = False
    try:
        ping_res = redis_client.ping()
        print(f"[Redis] Ping: {ping_res}")
        redis_ok = True
    except Exception as e:
        print(f"[Redis] [FAILED] Connection error: {e}")

    print("\n----------------------------------------")
    if db_ok and redis_ok:
        print("[SUCCESS] Both PostgreSQL and Redis connections are active and working!")
        sys.exit(0)
    else:
        print("[FAILURE] Please check your .env credentials and ensure local database/redis services are running.")
        sys.exit(1)


if __name__ == "__main__":
    verify_connections()
