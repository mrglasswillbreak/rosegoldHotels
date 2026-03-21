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

python manage.py collectstatic --no-input

# Ensure lowercase symlinks exist so Django templates can reference
# Allfiles/css/... and Allfiles/js/... (assets/ uses capital Css/Js/)
mkdir -p "assets/Allfiles/Css" "assets/Allfiles/Js"
ln -sfn "Css" "assets/Allfiles/css"
ln -sfn "Js" "assets/Allfiles/js"
ln -sfn "Style.css" "assets/Allfiles/Css/style.css"
ln -sfn "Responsive.css" "assets/Allfiles/Css/responsive.css"

python manage.py migrate
