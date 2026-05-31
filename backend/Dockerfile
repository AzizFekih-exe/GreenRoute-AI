FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/data

COPY backend/ ./backend/
COPY p1_chemistry_data/ ./p1_chemistry_data/
COPY p2_ai_ml/ ./p2_ai_ml/
COPY src/ ./src/

ENV PYTHONPATH=/app
ENV FLASK_APP=backend/app.py
ENV FLASK_ENV=production
ENV DB_PATH=/app/data/solvents.db

EXPOSE 5000

CMD ["python", "backend/app.py"]
