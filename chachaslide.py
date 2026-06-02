from collections.abc import Mapping, Sequence
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from rapidfuzz import process
from pydantic import BaseModel
from html import escape
# import faker               # NEW weird package 1
import redis
import os

redis_host = os.environ.get("REDIS_HOST", "redis-service")
r = redis.Redis(
    host=redis_host,
    port=6379,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

consultants = {
    'Sam': {'full name': 'Samuel Pekofsky', 'pod': 'Cha Cha Slide', 'rest': 1, 'cohort': 'DF14'}
    , 'Noelle': {'full name': 'Noelle Cierpilowski', 'pod': 'Cha Cha Slide', 'rest': None, 'cohort': 'DF14'}
    , 'Will': {'full name': 'William Francis', 'pod': 'Cha Cha Slide', 'rest': None, 'cohort': 'DF14'}
    , 'Sara': {'full name': 'Sara Noor', 'pod': 'Cha Cha Slide', 'rest': None, 'cohort': 'DF14'}
}

app = FastAPI()

HTML_VIEW_URL = "/?format=html"
JSON_VIEW_URL = "/?format=json"

def render_html_table(data) -> str:
    def format_cell(value) -> str:
        if value is None:
            return "Unknown"
        return escape(str(value))

    if isinstance(data, Mapping):
        if data and all(isinstance(value, Mapping) for value in data.values()):
            columns = ["Key"] + sorted({key for value in data.values() for key in value.keys()})
            rows = [
                "<tr>"
                + "".join(
                    f"<td>{format_cell(item)}</td>"
                    for item in ([key] + [value.get(column) for column in columns[1:]])
                )
                + "</tr>"
                for key, value in data.items()
            ]
        else:
            columns = ["Key", "Value"]
            rows = [
                f"<tr><td>{format_cell(key)}</td><td>{format_cell(value)}</td></tr>"
                for key, value in data.items()
            ]
    elif isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        if data and all(isinstance(item, Mapping) for item in data):
            columns = sorted({key for item in data for key in item.keys()})
            rows = [
                "<tr>"
                + "".join(f"<td>{format_cell(item.get(column))}</td>" for column in columns)
                + "</tr>"
                for item in data
            ]
        else:
            columns = ["Value"]
            rows = [f"<tr><td>{format_cell(item)}</td></tr>" for item in data]
    else:
        columns = ["Value"]
        rows = [f"<tr><td>{format_cell(data)}</td></tr>"]

    header_html = "".join(f"<th>{escape(column)}</th>" for column in columns)
    body_html = "".join(rows)

    return f"""
    <table>
        <thead>
            <tr>{header_html}</tr>
        </thead>
        <tbody>
            {body_html}
        </tbody>
    </table>
    """


def render_consultants_html(visits: int = 0) -> str:
    table_html = render_html_table(consultants)

    return f"""
    <html>
    <head>
        <title>Consultants</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 24px; }}
            table {{ border-collapse: collapse; width: 100%; max-width: 900px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top; }}
            th {{ background: #f4f4f4; }}
            .view-switch {{
                margin-top: 20px;
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
            }}
            .view-switch a {{
                display: inline-block;
                padding: 10px 14px;
                border: 1px solid #222;
                border-radius: 999px;
                color: #222;
                text-decoration: none;
                background: #fff;
            }}
            .view-switch a:hover {{
                background: #222;
                color: #fff;
            }}
        </style>
    </head>
    <body>
        <h1>Consultants</h1>
        {table_html}
        <div class="view-switch">
            <a href="{JSON_VIEW_URL}">View as JSON</a>
        </div>

        <h3>This page has {visits} visits.</h3>
    </body>
    </html>
    """


@app.get("/")
def home(format: str = Query("json", pattern="^(json|html)$")):
    # Track total visits across ALL pods
    try:
        visits = r.incr("counter")
    except redis.RedisError:
        visits = 0
    
    
    if format == "html":
        return HTMLResponse(content=render_consultants_html(visits))

    return consultants
    # return {
    #     "consultants": consultants,
    #     "_links": {
    #         "html": HTML_VIEW_URL,
    #         "json": JSON_VIEW_URL,
    #     },
    # }


@app.get("/health")
def health():
    return Response(content="OK", media_type="text/plain")


@app.get("/{consultant}")
def get_consultant(consultant: str, format: str = Query("json", pattern="^(json|html)$")):
    nick = consultant.capitalize()
    c = consultants[nick]
    if format == "html":
        return HTMLResponse(content=f"""
        <html>
        <head>
            <title>Consultant: {escape(nick)}</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 24px; }}
                table {{ border-collapse: collapse; width: 100%; max-width: 900px; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top; }}
                th {{ background: #f4f4f4; }}
            </style>
        </head>
        <body>
            <h1>{escape(nick)}</h1>
            {render_html_table(c)}
        </body>
        </html>
        """)

    return c


class Consultant(BaseModel):
    nick: str
    name: str
    pod: str | None
    rest: str | int | None
    cohort: str

def create_consultant_entry(consultant: Consultant):
    info = {
            'full name': consultant['name']
            , 'pod': consultant['pod']
            , 'rest': consultant['rest']
            , 'cohort': consultant['cohort']
    }
    return info


@app.post('/')
def add_consultant(consultant: Consultant):
    added_consultant = consultant.model_dump()
    # return {
    #     'a': added_consultant
    #     , 'b': isinstance(added_consultant, dict)
    # }
    if added_consultant['nick'] not in consultants:
        info = create_consultant_entry(add_consultant)
        consultants[str(added_consultant['nick'])] = info
    
        similar_name = process.extractOne(added_consultant['nick'], consultants.keys())

        return {
            'added': {added_consultant['nick']: consultants[added_consultant['nick']]}
            , 'most similar nick name': similar_name[0]
        }

    raise HTTPException(status_code=409, detail='Consultant already exists')

@app.put('/{nick}')
def update_consultant_by_nickname(nick: str, consultant: Consultant):
    prev = consultants[nick]
    changed_consultant = consultant.model_dump()
    consultants[nick] = create_consultant_entry(changed_consultant)
    similar_name = process.extractOne(changed_consultant['nick'], consultants.keys())
    return {
            'updated': {changed_consultant['nick']: consultants[changed_consultant['nick']]}
            , 'previous': {nick: prev}
            , 'most similar nick name': similar_name[0]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)