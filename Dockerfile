FROM python:3.12-slim

WORKDIR /code

# Install deps first so Docker caches this layer between code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# gunicorn serves the Flask app object at app.main:app
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app.main:app"]
