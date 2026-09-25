# Calculator API

Производительный REST API-калькулятор на FastAPI + Docker.

## Возможности

- `POST /api/v1/add` — сложение
- `POST /api/v1/subtract` — вычитание
- `POST /api/v1/multiply` — умножение
- `POST /api/v1/divide` — деление (с проверкой деления на ноль)
- `POST /api/v1/power` — возведение в степень
- `POST /api/v1/sqrt` — квадратный корень
- `POST /api/v1/calculate` — вычисление произвольного выражения, например `(2 + 3) * 4 / 2`
- `GET /api/v1/history` — история последних вычислений
- `GET /health` — health-check для Docker/Kubernetes
- `GET /docs` — автоматическая интерактивная документация (Swagger UI)

Особенности реализации:
- Асинхронные обработчики (async/await) — высокая пропускная способность
- Вычисление выражений через `ast`, а не `eval()` — защита от инъекций кода
- Несколько воркеров uvicorn в контейнере — использование нескольких ядер CPU
- Health-check встроен в сам образ
- Многоэтапная сборка Docker-образа — уменьшенный размер и без лишних инструментов сборки в финальном образе
- Запуск от непривилегированного пользователя внутри контейнера







##  Локальный запуск без Docker (для разработки)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка:
```bash
curl -X POST http://localhost:8000/api/v1/add -H "Content-Type: application/json" -d '{"a": 2, "b": 3}'
```

Запуск тестов:
```bash
pip install pytest httpx
pytest tests/ -v
```

##  Сборка Docker-образа

Из корня проекта (там, где лежит `Dockerfile`):

```bash
docker build -t calculator-api:latest .
```

Проверить, что образ создан:
```bash
docker images | grep calculator-api
```

##  Запуск контейнера локально

Вариант A — напрямую через `docker run`:
```bash
docker run -d \
  --name calculator-api \
  -p 8000:8000 \
  --restart unless-stopped \
  calculator-api:latest
```

Вариант B — через `docker-compose` (проще для повторяемых запусков):
```bash
docker compose up -d --build
```

Проверка, что контейнер запущен и здоров:
```bash
docker ps
docker logs calculator-api
curl http://localhost:8000/health
```

Открыть документацию API в браузере:
```
http://localhost:8000/docs
```

##  Примеры запросов

```bash
# Сложение
curl -X POST http://localhost:8000/api/v1/add \
  -H "Content-Type: application/json" \
  -d '{"a": 10, "b": 5}'

# Деление
curl -X POST http://localhost:8000/api/v1/divide \
  -H "Content-Type: application/json" \
  -d '{"a": 10, "b": 0}'
# -> 400 Bad Request: "Деление на ноль невозможно"

# Произвольное выражение
curl -X POST http://localhost:8000/api/v1/calculate \
  -H "Content-Type: application/json" \
  -d '{"expression": "(2 + 3) * 4 / 2"}'

# История вычислений
curl http://localhost:8000/api/v1/history
```

##  Остановка и удаление контейнера

```bash
docker stop calculator-api
docker rm calculator-api
# для docker-compose:
docker compose down
```

##  Публикация образа в реестр (Docker Hub / приватный реестр)

```bash
docker tag calculator-api:latest <ваш_логин>/calculator-api:latest
docker login
docker push <ваш_логин>/calculator-api:latest
```

##  Запуск в облаке

###  Любой VPS с Docker 
```bash
# на сервере
git clone <репозиторий>
cd calculator-api
docker compose up -d --build
```



## Требования к производительности

- Асинхронные обработчики FastAPI + несколько воркеров uvicorn обеспечивают
  параллельную обработку запросов на нескольких ядрах CPU.
- Многоэтапная сборка Docker снижает размер финального образа (компиляторы
  остаются только в промежуточном слое builder).
- Health-check позволяет оркестратору (Docker/Kubernetes/ECS) автоматически
  перезапускать нездоровые контейнеры.
- Ограничение ресурсов контейнера задаётся в `docker-compose.yml` (`cpus`, `memory`)
  — при необходимости настройте под вашу нагрузку.
