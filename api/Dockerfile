FROM python:3.12-slim

WORKDIR /app

# Системные зависимости для opencv + ffmpeg (для рендера/запекания)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY api/ ./api/
COPY db/ ./db/
COPY scripts/ ./scripts/
COPY training-skill/ ./training-skill/
COPY exercisedb_data/exercise_db_final.json ./exercisedb_data/exercise_db_final.json

# Медиа и бэкапы — НЕ копируем в образ (монтируется volume-ом)
# exercisedb_data/mp4_paused → volume

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
