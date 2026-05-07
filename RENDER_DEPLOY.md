# Render deploy

## Что уже настроено

- `render.yaml` создает web service `site-toi` и бесплатную PostgreSQL базу `site-toi-db`.
- `build.sh` ставит зависимости, собирает статику и запускает миграции.
- `.python-version` фиксирует Python `3.13`.
- `settings.py` автоматически использует Render PostgreSQL через `DATABASE_URL`, WhiteNoise для статики и `RENDER_EXTERNAL_HOSTNAME` для `ALLOWED_HOSTS`.

## Что нужно заполнить в Render

После создания Blueprint открой Environment у сервиса `site-toi` и добавь значение:

```text
GOOGLE_DRIVE_TOKEN_JSON
```

Туда нужно вставить содержимое файла `google-drive-token.json` целиком. Этот файл нельзя коммитить в Git.

Проверь, что есть:

```text
GOOGLE_DRIVE_STORAGE=true
GOOGLE_DRIVE_FOLDER_ID=13HHHHfLsKXHrOxUcxLSk7YVTA94b-EEs
DEBUG=false
```

## Команды Render

Build Command:

```bash
bash build.sh
```

Start Command:

```bash
gunicorn backend.wsgi:application
```

Health Check Path:

```text
/healthz/
```

## Важно для тестового Free плана

Free web service может засыпать после простоя, поэтому первый заход иногда открывается долго. Free PostgreSQL подходит для теста, но не для настоящего тоя: перед реальным использованием лучше перейти на платный план.
