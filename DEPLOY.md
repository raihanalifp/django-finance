# Deploy Guide (Ubuntu VPS)

This guide uses Gunicorn + Nginx and builds Tailwind on the server.

## 1) System Packages
```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential nginx nodejs npm
```

## 2) App Setup
```bash
cd /var/www/django-finance
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3) Environment Variables
Create a `.env` file in the project root (same level as `manage.py`) based on `.env.example`,
or export the variables in the shell. `python-decouple` will read `.env` automatically.

```bash
export DJANGO_DEBUG=0
export DJANGO_SECRET_KEY="change-me"
export DJANGO_ALLOWED_HOSTS="your-domain.com,localhost,127.0.0.1"
export DJANGO_CSRF_TRUSTED_ORIGINS="https://your-domain.com"

export DJANGO_DB_ENGINE="django.db.backends.postgresql"
export DJANGO_DB_NAME="django_finance"
export DJANGO_DB_USER="postgres"
export DJANGO_DB_PASSWORD="change-me"
export DJANGO_DB_HOST="127.0.0.1"
export DJANGO_DB_PORT="5432"
```

## 4) Build Tailwind CSS
```bash
npm install
npm run build
```

## 5) Django Migrate + Collectstatic
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## 6) Run Gunicorn
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## 7) Nginx (Optional)
Proxy requests to Gunicorn and serve `/static/` from `staticfiles/`.
