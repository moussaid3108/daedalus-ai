#!/bin/sh
exec gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 2 --timeout 120 app:app
