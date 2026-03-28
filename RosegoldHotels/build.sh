#!/usr/bin/env bash
# Render build script for Hotel Management System
set -o errexit

# Ensure we run from the script's own directory
cd "$(dirname "$0")"

pip install --upgrade pip
pip install -r requirements.txt

# Build the frontend only when a standalone app exists in this repo.
if [ -f "frontend/package.json" ]; then
  cd frontend
  npm ci
  npm run build
  cd ..
else
  echo "No frontend app found; skipping frontend build."
fi

# Ensure lowercase aliases exist when the filesystem treats them as distinct
# names. On case-insensitive filesystems, `css`/`Css` resolve to the same path,
# so forcing the symlink would create a loop like `Css/Css -> Css`.
mkdir -p "assets/Allfiles/Css" "assets/Allfiles/Js"
if [ ! -e "assets/Allfiles/css" ]; then
  ln -s "Css" "assets/Allfiles/css"
fi
if [ ! -e "assets/Allfiles/js" ]; then
  ln -s "Js" "assets/Allfiles/js"
fi

python manage.py collectstatic --no-input

python manage.py migrate

# Optionally create a default superuser if requested via environment variables.
# To enable, set CREATE_DEFAULT_SUPERUSER=1 and provide SUPERUSER_EMAIL and
# SUPERUSER_PASSWORD in the environment before running this script.
if [ "${CREATE_DEFAULT_SUPERUSER:-}" = "1" ]; then
  python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()

email = os.environ.get('SUPERUSER_EMAIL')
password = os.environ.get('SUPERUSER_PASSWORD')

if not email or not password:
    raise SystemExit('SUPERUSER_EMAIL and SUPERUSER_PASSWORD must be set when CREATE_DEFAULT_SUPERUSER=1')

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
    print('Superuser created.')
else:
    print('Superuser already exists.')
"
fi
