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


## Версионирование и CI/CD

Версия хранится в файле `VERSION` (например `1.2.3`) и прокидывается в Docker-образ
как build-arg `APP_VERSION`, попадая в `LABEL` образа и в ответ эндпоинта `GET /api/v1/version`.

### Правила коммитов (Conventional Commits)

Пайплайн сам решает, как поднять версию, читая сообщения коммитов от последнего тега:

| Префикс коммита                          | Что это значит                                   | Bump  |
|-------------------------------------------|--------------------------------------------------|-------|
| `feat: ...`                               | новый метод/функциональность калькулятора        | minor |
| `fix: ...`                                | исправление бага                                  | patch |
| `chore(deps): ...` / `fix(docker): ...`   | переход на новую версию компонента/базового образа| patch |
| `feat!: ...` или тело коммита с `BREAKING CHANGE` | несовместимые изменения API                | major |

Пример: добавили новый эндпоинт `/api/v1/modulo` → коммит `feat: add modulo endpoint` →
пайплайн сам поднимет версию `1.2.0 → 1.3.0`.

### Как работает пайплайн (`Jenkinsfile`)

При каждом пуше в ветку `main` (через webhook) Jenkins автоматически:

1. **Checkout** — забирает код из репозитория.
2. **Test** — прогоняются юнит-тесты; если падают — пайплайн останавливается, версия не трогается.
3. **Determine next version** — `scripts/bump_version.sh` анализирует коммиты и вычисляет новую версию.
4. **Commit & tag version** — обновляет `VERSION`, коммитит (`chore(release): bump version to X.Y.Z [skip ci]`) и ставит git-тег `vX.Y.Z`, пушит обратно в GitHub.
5. **Build image** — собирает локальный Docker-образ: `docker build --build-arg APP_VERSION=X.Y.Z -t calculator-api:X.Y.Z -t calculator-api:latest .`

Публикация образа в реестр и деплой на сервер не входят в пайплайн — нет своего реестра
и сервера для этого проекта. Если понадобится позже, пример этих стадий есть ..
закомментированным в конце `Jenkinsfile`.

Проверить, что образ собрался и завести его, уже запустив вручную:
```bash
docker images | grep calculator-api
docker run -d -p 8000:8000 calculator-api:latest
curl http://localhost:8000/api/v1/version
```

### Автообновление версий зависимостей и базовых образов

Файл `renovate.json` настраивает [Renovate](https://docs.renovatebot.com/) на:
- еженедельную проверку `requirements.txt` (FastAPI, uvicorn, pydantic) и открытие PR при выходе новых версий;
- отслеживание обновлений базового образа `python:3.12-slim` в `Dockerfile`;
- отдельную маркировку major-обновлений (`needs-review`) — они не сливаются автоматически.

Когда такой PR сливается в `main`, `Jenkinsfile` сам прогоняет тесты на новых версиях
компонентов, бампает версию калькулятора (`patch`, префикс `fix(deps):`/`fix(docker):`)
и публикует пересобранный образ.

## Что нужно установить и настроить, чтобы Jenkinsfile заработал

Ничего скачивать в сам проект не нужно — весь список ниже про инфраструктуру Jenkins,
которая обычно разворачивается один раз на команду/сервер.

### 1. Сам Jenkins-сервер

Нужен где-то работающий Jenkins. Самый быстрый способ — поднять его в Docker:

```bash
docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts-jdk17
```

Второй volume (`docker.sock`) нужен, чтобы Jenkins мог изнутри вызывать `docker build`/`docker push`
на сборочном агенте. Если Jenkins ставится не в контейнере, а на сервер напрямую — достаточно
установить Java 17+ и сам Jenkins по инструкции с [jenkins.io](https://www.jenkins.io/download/).

После запуска откройте `http://<адрес-сервера>:8080` — Jenkins попросит начальный пароль
(смотрите в логах контейнера: `docker logs jenkins`) и предложит установить стандартный
набор плагинов при первом входе.

### 2. Docker Engine на агенте, где выполняется сборка

Так как `Jenkinsfile` вызывает `docker build`/`docker push`, на машине-агенте должен быть
установлен Docker Engine. Если Jenkins запущен в контейнере с примонтированным `docker.sock`
(как в команде выше) — отдельно ничего ставить не нужно, он использует Docker хост-машины.

### 3. Плагины Jenkins (ставятся один раз: *Manage Jenkins → Plugins*)

| Плагин | Зачем нужен |
|---|---|
| **Pipeline** | выполнение `Jenkinsfile` (обычно уже входит в стандартный набор) |
| **Git** | checkout репозитория |
| **Credentials Binding** | подстановка логина/токена в `withCredentials` |

### 4. Учётные данные (*Manage Jenkins → Credentials*) — под именем из `Jenkinsfile`

| ID credential | Тип | Зачем |
|---|---|---|
| `git-push-credentials` | Username with password (логин GitHub + Personal Access Token) | пуш обновлённого `VERSION` и тега обратно в репозиторий |

Публикация образа в реестр и деплой на сервер в текущей версии `Jenkinsfile` не используются
(нет своего реестра и сервера) — соответственно, `docker-registry-creds` и `deploy-ssh-key`
заводить не нужно. Пример, как добавить эти стадии обратно, если реестр/сервер появятся —
в комментарии в конце `Jenkinsfile`.

### 5. Job в Jenkins

Создайте **Pipeline** job (New Item → Pipeline) с источником "Pipeline script from SCM",
укажите URL вашего GitHub-репозитория — Jenkins сам найдёт `Jenkinsfile` в корне проекта.

### 6. Webhook на репозитории (чтобы пайплайн запускался автоматически на каждый push)

В настройках GitHub-репозитория (Settings → Webhooks → Add webhook) добавьте webhook
на `http://<адрес-jenkins>:8080/github-webhook/`. Это и реализует требование "автоматически
при каждом пуше кода". Если Jenkins крутится локально (как сейчас), для доступа GitHub к
вашему `localhost` понадобится туннель (например, `ngrok`) — либо для учебных целей можно
обойтись ручным нажатием **Build Now** после каждого push.

### 7. GitHub Personal Access Token для `git-push-credentials`

Создайте токен: GitHub → Settings → Developer settings → Personal access tokens →
Tokens (classic) → Generate new token, с правом `repo`. В Jenkins добавьте Credential типа
**Username with password**: username — ваш логин GitHub, password — сам токен.

Больше ничего скачивать не требуется — само приложение (Python/FastAPI) не нужно ставить
на хост Jenkins, оно целиком собирается и запускается внутри Docker-образа.

## Требования к производительности

- Асинхронные обработчики FastAPI + несколько воркеров uvicorn обеспечивают
  параллельную обработку запросов на нескольких ядрах CPU.
- Многоэтапная сборка Docker снижает размер финального образа (компиляторы
  остаются только в промежуточном слое builder).
- Health-check позволяет оркестратору (Docker/Kubernetes/ECS) автоматически
  перезапускать нездоровые контейнеры.
- Ограничение ресурсов контейнера задаётся в `docker-compose.yml` (`cpus`, `memory`)
  — при необходимости настройте под вашу нагрузку.
