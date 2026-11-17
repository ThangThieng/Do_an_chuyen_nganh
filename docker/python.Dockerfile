# Image Python dùng chung cho init (migrate + nạp CSV thật + backfill + tài khoản), etl (scheduler) và backend (FastAPI)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Font DejaVu có dấu tiếng Việt cho xuất PDF (ReportLab)
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY common ./common
COPY database ./database
COPY ingest ./ingest
COPY etl ./etl
COPY backend ./backend
COPY tools ./tools
COPY docker/bootstrap.sh ./docker/bootstrap.sh

# Chạy bằng user thường; thư mục sao lưu cần quyền ghi
RUN sed -i 's/\r$//' docker/bootstrap.sh \
    && useradd --create-home --uid 10001 app \
    && mkdir -p backups \
    && chown -R app:app backups
USER app

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
