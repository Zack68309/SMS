# Zack SMS

A small Django app that sends SMS through the Nalo SMS API and shows delivery reports as they arrive.

- Send to one or more numbers, choosing a **sender ID** from a dropdown
- Receives Nalo **callbacks** (submission result and delivery reports) at `/sms-callback/`
- **Message history** that refreshes every 5 seconds
- Runs in **Docker**; config comes from environment variables only

## Run it with Docker

```bash
cp .env.example .env        # then set SMS_API_KEY and SENDER_IDS
docker compose up --build
```

Open http://localhost:8000.

### Getting delivery reports locally

Nalo can't reach `localhost`, so start the app with a free Cloudflare quick tunnel:

```bash
docker compose --profile tunnel up --build
docker compose logs tunnel | grep trycloudflare
```

Open the printed `https://….trycloudflare.com` URL in your browser and send from there. The app uses the address you opened it on as the callback URL, so you don't need to set `CALLBACK_BASE_URL`. The URL changes every time the tunnel restarts.

ngrok works the same way: `ngrok http 8000`, then open the ngrok URL.

## Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `SMS_API_KEY` | yes | Nalo API key |
| `SENDER_IDS` | yes | Comma-separated sender IDs for the dropdown (must be registered on the account) |
| `SMS_API_URL` | no | Nalo send-message endpoint |
| `CALLBACK_BASE_URL` | no | Public base URL for callbacks, e.g. `https://my-app.onrender.com`. Empty = use the URL the page was opened on |
| `DJANGO_SECRET_KEY` | yes in production | Long random string |
| `DJANGO_DEBUG` | no | `True` for development only |
| `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` | no | Defaults allow localhost, trycloudflare, ngrok and onrender |
| `DATABASE_URL` | no | Postgres URL (e.g. free Neon/Supabase). Default: SQLite in a Docker volume |
| `DEFAULT_COUNTRY_CODE` | no | Used to convert local `0XX…` numbers. Default `233` |

## Deploying (Render, free)

1. Push this repo to GitHub (`.env` is git-ignored; never commit it).
2. On Render: **New → Web Service**, pick the repo; it detects the `Dockerfile`.
3. Add the environment variables above. Set `DATABASE_URL` to a free Neon/Supabase Postgres, because Render's free disk is wiped on restart.
4. Set `CALLBACK_BASE_URL` to the Render URL.

## Endpoints

| Path | Purpose |
| --- | --- |
| `/` | Send form and history |
| `/sms-callback/` | Nalo posts callbacks here (POST, JSON) |
| `/api/messages/` | Latest 50 messages as JSON |
| `/admin/` | Django admin (`docker compose exec app python manage.py createsuperuser`) |
