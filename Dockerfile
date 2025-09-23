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

# Set up a virtual environment to isolate dependencies and avoid the root user warning.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install system dependencies for audio processing and file type identification.
# ffmpeg is crucial for handling various audio formats.
# libmagic1 helps with MIME type detection.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libmagic1 && rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the application for better security.
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

COPY --from=builder /app/wheels /wheels
# Installing into the venv will not trigger the root user warning.
RUN pip install --no-cache /wheels/*

# Copy the application code and set the correct ownership.
COPY --chown=app:app . .

# Switch to the non-root user.
USER app

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app"]