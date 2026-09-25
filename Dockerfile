# syntax=docker/dockerfile:1

# сборка зависимостей 
FROM python:3.12-slim AS builder

WORKDIR /build

# Устанавливаем системные зависимости, нужные только для сборки колёс
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

#  рабочий образ (минимальный, без компиляторов) 
FROM python:3.12-slim

# Непривилегированный пользователь для запуска приложения 
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Переносим уже собранные Python-пакеты из этапа builder
COPY --from=builder /root/.local /home/appuser/.local

# Копируем код приложения
COPY app ./app

# Права на директорию для непривилегированного пользователя
RUN chown -R appuser:appuser /app

USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Проверка работоспособности контейнера
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Несколько воркеров uvicorn для повышения производительности под нагрузкой
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
