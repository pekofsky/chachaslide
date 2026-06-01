from fastapi import FastAPI, Response
import faker               # NEW weird package 1
import emoji               # NEW weird package 2
import redis
import os
import random

app = FastAPI()

# Faker instance
fake = faker.Faker()

# Redis setup
redis_host = os.environ.get("REDIS_HOST", "redis-service")
r = redis.Redis(
    host=redis_host,
    port=6379,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

@app.get("/")
def home():
    # Track total visits across ALL pods
    try:
        visits = r.incr("counter")
    except redis.RedisError:
        visits = 0

    # Generate random fake identity
    name = fake.name()
    job = fake.job()

    # Random emoji
    random_emoji = random.choice(["🚀", "🔥", "🤖", "🌍", "🎲"])
    emoji_text = emoji.emojize(random_emoji)

    return {
        "message": "Welcome to the weird Kubernetes app!",
        "person": {
            "name": name,
            "job": job
        },
        "emoji": emoji_text,
        "visits": visits
    }

@app.get("/health")
def health():
    return Response(content="OK", media_type="text/plain")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)