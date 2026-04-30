FROM python:3.11-slim

WORKDIR /app

CMD ["python", "-m", "app.main"]
