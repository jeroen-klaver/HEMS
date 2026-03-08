FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer cached unless requirements.txt changes)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend package (preserves 'backend/' as a Python package)
COPY backend/ backend/

# SQLite database and config live in a volume mounted at /data
ENV HEMS_DATA_DIR=/data

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
