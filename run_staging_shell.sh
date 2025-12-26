#!/bin/bash
# Run Django shell on staging
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || . venv/bin/activate
export DJANGO_ENV=staging
python manage.py shell
