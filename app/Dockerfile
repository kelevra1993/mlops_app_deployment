# Use the official Python 3.13 slim image as the base
FROM python:3.13-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the uv binary from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy your dependency configuration files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install the dependencies strictly from the lockfile
RUN uv sync --frozen --no-dev

# Copy the rest of your application code
COPY . .

# Expose the default Gradio port
EXPOSE 7860

# Force Gradio to listen on all network interfaces (required for Docker/Kubernetes)
ENV GRADIO_SERVER_NAME="0.0.0.0"

# Command to run the application
CMD ["uv", "run", "python", "gradio/gradio_app.py"]