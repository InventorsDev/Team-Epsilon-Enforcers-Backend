# --- Stage 1: Build Stage ---
# Use an official Python runtime as a parent image
FROM python:3.10-slim as builder

# Set the working directory in the container
WORKDIR /app

# Install build dependencies
RUN pip install --upgrade pip

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# --- Stage 2: Final Stage ---
FROM python:3.10-slim

WORKDIR /app

COPY --from=builder /app/wheels /wheels
COPY . .
RUN pip install --no-cache /wheels/*

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--host", "0.0.0.0", "--port", "8000"]