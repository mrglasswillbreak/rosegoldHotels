#!/usr/bin/env bash
# Render build script for Hotel Management System
set -o errexit

# Ensure we run from the script's own directory
cd "$(dirname "$0")"

pip install --upgrade pip
pip install -r requirements.txt

# Build the React frontend
cd frontend
npm ci
npm run build
cd ..

# Ensure lowercase symlinks exist so Django templates can reference
# Allfiles/css/... and Allfiles/js/... (assets/ uses capital Css/Js/)
mkdir -p "assets/Allfiles/Css" "assets/Allfiles/Js"
ln -sfn "Css" "assets/Allfiles/css"
ln -sfn "Js" "assets/Allfiles/js"

python manage.py collectstatic --no-input

python manage.py migrate

# Create default superuser if it does not already exist
python manage.py shell -c "
from HotelApp.models import Authorregis
if not Authorregis.objects.filter(email='superuser@rosegold.com').exists():
    Authorregis.objects.create_superuser(email='superuser@rosegold.com', password='Superuser')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"
