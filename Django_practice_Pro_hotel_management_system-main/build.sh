#!/usr/bin/env bash
# Render build script for Hotel Management System
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Build the React frontend
cd frontend
npm install
npm run build
cd ..

python manage.py collectstatic --no-input
python manage.py migrate
