FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# (kept for assignment requirement)
RUN python -m textblob.download_corpora

COPY chachaslide.py .

EXPOSE 5000

CMD ["uvicorn", "chachaslide:app", "--host", "0.0.0.0", "--port", "5000"]
