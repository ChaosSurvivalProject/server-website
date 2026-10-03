FROM python:3.14-slim

WORKDIR /app

# Install dependencies
# 注意：构建上下文是项目根目录（docker-compose.yml 的 context: ..），
# 所以这里必须写 backend/requirements.txt，不能写 requirements.txt
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/

# Create data directory
RUN mkdir -p /app/data

EXPOSE 5000

CMD ["python", "backend/run.py"]