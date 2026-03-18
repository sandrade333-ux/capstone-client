# Capstone Client

Sam's business management system.
Standalone Django app with Microsoft Entra ID sign-in.

## Quick start

```bash
git clone ... && cd capstone-client
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py seed
python manage.py runserver
# Open http://localhost:8000/admin/
```

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

```bash
AZURE_TENANT_ID=your-directory-tenant-id
AZURE_CLIENT_ID=your-application-client-id
AZURE_CLIENT_SECRET=your-client-secret-value
```

### Step 3: Restart and sign in

```bash
python manage.py runserver
# Open http://localhost:8000/oauth2/login
# Or click "Sign in with Microsoft" in the nav bar
```

Without Entra credentials, the app falls back to Django admin login at `/admin/login/`.

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

## Running tests

```bash
python manage.py test tests
```
