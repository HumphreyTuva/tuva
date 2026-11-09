# TUVA

TUVA is a React/Vite storefront backed by Django REST Framework. Product prices are stored and shown in Kenyan shillings (KSh). Checkout charges that KES amount through Safaricom M-PESA STK Push.

## Local setup

1. Copy `backend/.env.example` to `backend/.env` and set a unique `SECRET_KEY`. Add the Google, Daraja, Anthropic, and SMTP settings you intend to use. Never commit `.env`.
2. Set `MPESA_ENV=sandbox` for testing, and configure a public HTTPS `MPESA_CALLBACK_URL`.
3. For the shopping assistant, add either `GEMINI_API_KEY`/`GEMINI_MODEL` or the legacy `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` in `backend/.env`; Gemini automatically tries `GEMINI_FALLBACK_MODEL` (default `gemini-3.5-flash-lite`) if its primary model is temporarily overloaded, without waiting through repeated retries. Restart the backend after changing settings.
4. From `backend`, install dependencies and initialize the database:

   ```powershell
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   .\venv\Scripts\python.exe manage.py migrate
   .\venv\Scripts\python.exe manage.py seed
   .\venv\Scripts\python.exe manage.py runserver
   ```

   Create the virtual environment first with `python -m venv venv` when needed. The migration history is committed with the project.
4. Run Redis and a Celery worker for branded email delivery and restock alerts:

   ```powershell
   celery -A config worker -l info
   ```

5. From `frontend`, copy `.env.example` to `.env`, configure `VITE_GOOGLE_CLIENT_ID` and `VITE_WHATSAPP`, then run `npm install` and `npm run dev`. Configure `VITE_API` for the deployed API origin.

## Store dashboard

- Open the custom React store dashboard with **Ctrl+Shift+A**. On a touch device, press and hold the TUVA logo for about one second.
- Sign in with a Django staff account. Create one from `backend` with `.\venv\Scripts\python.exe manage.py createsuperuser`; only staff accounts can access dashboard data or actions.
- The dashboard summarizes sales, orders, stock alerts, and support conversations; staff can add, edit, and delete products, update stock quantities, and reply to live-chat messages. Products with existing orders cannot be deleted.
- Customers and staff can sign out from the storefront or dashboard; signing out revokes the active API token.

## Operations

- Google sign-in requires the same OAuth client ID in `GOOGLE_CLIENT_ID` (backend token verification) and `VITE_GOOGLE_CLIENT_ID` (frontend button).
- The AI shopping assistant supports Gemini via `GEMINI_API_KEY` and falls back to Anthropic if needed; restart the backend after setting any provider key.
- Set Daraja consumer credentials, shortcode, Till, passkey, and the callback URL in the backend environment. Do not expose Daraja credentials in frontend variables.
- Configure SMTP and Redis in production. Without SMTP, email uses Django's console backend; queued email and restock alerts require a running Celery worker.
- Customer support messages are stored in the database. Staff can review conversations and reply by adding a `Support` message with the same conversation UUID in Django admin.
- For production, set `DEBUG=0`, a unique secret, the correct `ALLOWED_HOSTS`, trusted `CORS_ALLOWED_ORIGINS`, HTTPS, and PostgreSQL using `DB_ENGINE=django.db.backends.postgresql` with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`. `CACHE_URL` can point at Redis for shared API caching.
- PWA installation is offered by supported browsers when the app is served over HTTPS (or localhost). On iOS, use Safari's **Add to Home Screen** action.
