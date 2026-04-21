FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV LENA_BOOTSTRAP_RUNTIME_FROM_SCRAPER=false
ENV LENA_STT_PROVIDER=mock
ENV LENA_REWRITE_PROVIDER=template
ENV LENA_TTS_PROVIDER=mock

EXPOSE 8000

CMD ["python", "-m", "app", "--host", "0.0.0.0", "--port", "8000", "--no-reload"]
