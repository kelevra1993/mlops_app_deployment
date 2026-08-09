# Use the official Python 3.13 slim image as the base
FROM python:3.13-slim

# Install system dependencies required by standard opencv-python.
# (If you switch to opencv-python-headless in pyproject.toml, you can delete this RUN block).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory to the parent of 'app' so that imports like `app.utilities` work
WORKDIR /src/app

# Copy the uv binary from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy your dependency configuration files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install the dependencies strictly from the lockfile
RUN uv sync --frozen --no-dev

# Copy the application code into their respective directories to preserve structure
COPY utilities/ ./utilities/
COPY data/ ./data/
COPY main/ ./main/

# Expose the default Gradio port
EXPOSE 7860

# Force Gradio to listen on all network interfaces
ENV GRADIO_SERVER_NAME="0.0.0.0"

# Set PYTHONPATH to /src so Python recognizes 'app' as a top-level module
ENV PYTHONPATH="/src"

# Command to run the application dynamically based on the APP_TYPE env var
# Note: Uvicorn syntax is <module>:<variable>, so it is app.main.api_app:app
CMD ["/bin/bash", "-c", "if [ \"$APP_TYPE\" = \"api\" ]; then /src/app/.venv/bin/uvicorn main.api_app:app --host 0.0.0.0 --port 8000; else /src/app/.venv/bin/python main/gradio_app.py; fi"]