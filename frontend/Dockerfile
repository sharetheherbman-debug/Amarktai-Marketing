FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN reflex init --name amarktai_dashboard --template blank 2>/dev/null || true
EXPOSE 3000 8000
CMD ["reflex", "run", "--env", "prod", "--backend-only"]
