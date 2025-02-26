FROM python:3.11-slim AS builder

WORKDIR /app

# Copy requirements first for better caching
COPY setup.py pyproject.toml ./
COPY README.md ./
COPY src/ ./src/

# Install build dependencies and build wheel
RUN pip install --no-cache-dir build
RUN python -m build --wheel

# Create the final image with minimal size
FROM python:3.11-slim

WORKDIR /app

# Copy built wheel from builder stage
COPY --from=builder /app/dist/*.whl ./

# Install the wheel with all optional dependencies
RUN pip install --no-cache-dir *.whl[all] && \
    rm -f *.whl

# Add a non-root user
RUN useradd -m devops
USER devops

# Set entrypoint to the CLI
ENTRYPOINT ["devops"]
CMD ["--help"]
