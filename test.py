from app.db.database import engine
from app.db.redis import redis_client

print(engine)

print(redis_client.ping())