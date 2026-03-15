#!/usr/bin/env bash
# build.sh – Render build script for the Hotel Management System
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
