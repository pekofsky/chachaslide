import os
import random
import json
from datetime import datetime

import redis
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

# -------- CONFIG --------
REDIS_HOST = os.getenv("REDIS_HOST", "redis-service")
APP_MESSAGE = os.getenv("APP_MESSAGE", "ChaChaSlide Game 🎮")

r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

app = FastAPI(title="ChaChaSlide Memory Game")

MOVES = ["l", "r", "u", "d"]

# -------- HEALTH --------
@app.get("/health")
def health():
    try:
        r.ping()
        return {"status": "ok"}
    except:
        return {"status": "error"}


# -------- GAME LOGIC --------
def generate_sequence(length=3):
    return [random.choice(MOVES) for _ in range(length)]


# -------- ROOT (GAME UI) --------
@app.get("/", response_class=HTMLResponse)
def home():
    return f"""
    <html>
    <head>
        <title>ChaChaSlide Game</title>
    </head>
    <body style="font-family:Arial; text-align:center;">
        <h1>{APP_MESSAGE}</h1>
        <p>Repeat the sequence!</p>

        <button onclick="startGame()">Start Game</button>

        <h2 id="sequence"></h2>

        <input id="answer" placeholder="Enter sequence e.g. lrud"/>
        <br><br>

        <button onclick="submitAnswer()">Submit</button>

        <h3 id="result"></h3>

        <h3>Leaderboard</h3>
        <div id="leaderboard"></div>

        <script>
            let currentSeq = ""

            async function startGame() {{
                const res = await fetch('/start')
                const data = await res.json()

                currentSeq = data.sequence.join('')
                document.getElementById('sequence').innerText = currentSeq

                setTimeout(() => {{
                    document.getElementById('sequence').innerText = "???"
                }}, 2000)
            }}

            async function submitAnswer() {{
                const answer = document.getElementById('answer').value

                const res = await fetch('/check', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ answer: answer }})
                }})

                const data = await res.json()

                document.getElementById('result').innerText = data.message

                loadLeaderboard()
            }}

            async function loadLeaderboard() {{
                const res = await fetch('/leaderboard')
                const data = await res.json()

                let html = ""
                data.scores.forEach(s => {{
                    html += `<p>${{s.user}}: ${{s.score}}</p>`
                }})

                document.getElementById('leaderboard').innerHTML = html
            }}

            loadLeaderboard()
        </script>
    </body>
    </html>
    """


# -------- START GAME --------
@app.get("/start")
def start():
    seq = generate_sequence(4)
    r.set("current_sequence", json.dumps(seq))

    return {"sequence": seq}


# -------- CHECK ANSWER --------
@app.post("/check")
async def check(request: Request):
    body = await request.json()
    answer = body.get("answer", "")

    correct_seq = json.loads(r.get("current_sequence") or "[]")
    correct_string = "".join(correct_seq)

    if answer == correct_string:
        score = len(correct_seq)

        # store leaderboard
        entry = {
            "user": "Player",
            "score": score,
            "time": str(datetime.utcnow())
        }

        r.lpush("leaderboard", json.dumps(entry))

        return {"message": f"✅ Correct! Score: {score}"}
    else:
        return {"message": "❌ Wrong sequence!"}


# -------- LEADERBOARD --------
@app.get("/leaderboard")
def leaderboard():
    scores = r.lrange("leaderboard", 0, 9)

    return {
        "scores": [json.loads(s) for s in scores]
    }
