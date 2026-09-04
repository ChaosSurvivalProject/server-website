FROM python:3.14-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/

# Create data directory
RUN mkdir -p /app/data

EXPOSE 5000

CMD ["python", "backend/run.py"]