from flask import jsonify
from fastapi import FastAPI
from pydantic import BaseModel
import faker  # NEW weird package 1
import emoji  # NEW weird package 2
import redis
import os
import random

app = FastAPI()

# Faker instance
fake = faker.Faker()

# Redis setup
redis_host = os.environ.get("REDIS_HOST", "redis-service")
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)


@app.get("/")
def home():
    # Track total visits across ALL pods
    visits = r.incr("counter")

    # Generate random fake identity
    name = fake.name()
    job = fake.job()

    # Random emoji
    random_emoji = random.choice(["🚀", "🔥", "🤖", "🌍", "🎲"])
    emoji_text = emoji.emojize(random_emoji)

    return jsonify(
        {
            "message": "Welcome to the weird Kubernetes app!",
            "person": {"name": name, "job": job},
            "emoji": emoji_text,
            "visits": visits,
        }
    )


@app.get("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
