FROM python:3.10-slim

# Playwright dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg curl unzip libnss3 libxss1 libasound2 \
    fonts-liberation xdg-utils libgbm1 libgtk-3-0 \
    && apt-get clean

WORKDIR /app

COPY app/ /app/

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    playwright install --with-deps chromium

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
