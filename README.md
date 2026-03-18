# Capstone Client

Sam's business management system.
Standalone Django app with Microsoft Entra ID sign-in.

## Quick Start (Docker Desktop)

### Prerequisites

- Docker Desktop installed and running
- A Microsoft Entra app registration (see Entra Setup below)

### 1. Configure environment

```bash
git clone ... && cd capstone-client
cp .env.example .env
```

Open `.env` and fill in your 3 Entra values:

```
AZURE_TENANT_ID=your-directory-tenant-id
AZURE_CLIENT_ID=your-application-client-id
AZURE_CLIENT_SECRET=your-client-secret-value
```

### 2. Start the app

```bash
docker compose up --build
```

### 3. Initialize the database

In a new terminal:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed
```

### 4. Open the app

Go to http://localhost:8000/oauth2/login and sign in with Microsoft.

Or click "Sign in with Microsoft" in the nav bar.

### Subsequent runs

```bash
docker compose up
```

No `--build` needed after first time (only rebuild when `requirements.txt` or `Dockerfile` changes).

### Stop the app

```bash
docker compose down
```

### Useful commands

```bash
# Run tests:
docker compose exec web python manage.py test tests

# Django shell:
docker compose exec web python manage.py shell

# View logs:
docker compose logs -f web
```

---

## Sign in with Microsoft (Entra ID)

### Step 1: Register an app in Microsoft Entra ID

1. Go to [entra.microsoft.com](https://entra.microsoft.com) and sign in
2. Navigate to **Applications** > **App registrations** > **New registration**
3. Fill in:
   - **Name**: `Capstone Client`
   - **Supported account types**: "Accounts in this organizational directory only"
   - **Redirect URI**: Select **Web**, enter `http://localhost:8000/oauth2/callback`
4. Click **Register**
5. Copy **Application (client) ID** and **Directory (tenant) ID** from the overview page
6. Go to **Certificates & secrets** > **New client secret** > copy the **Value**

### Step 2: Add credentials to .env

```
AZURE_TENANT_ID=your-directory-tenant-id
AZURE_CLIENT_ID=your-application-client-id
AZURE_CLIENT_SECRET=your-client-secret-value
```

### Step 3: Restart and sign in

```bash
docker compose down && docker compose up
```

Go to http://localhost:8000/oauth2/login.

Without Entra credentials, the app falls back to Django admin login at `/admin/login/`.

---

## Apps

- **crm/** — Companies, contacts, interactions
- **jobs/** — Work orders and job notes
- **billing/** — Invoices, void requests, disputes
- **sync/** — Connection to Tyler's control plane (optional)

## Connecting to Tyler

In Django admin > Sync > Add Sync Configuration:
- Control plane URL: (ask Tyler)
- Shared secret: (ask Tyler)
- Instance ID: your business slug (e.g. "entropyopposition")

---

## Local Development (without Docker)

If you prefer running without Docker:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DATABASE_URL to a local PostgreSQL (or leave unset for SQLite)
python manage.py migrate
python manage.py createsuperuser
python manage.py seed
python manage.py runserver
# Open http://localhost:8000/admin/
```
