#!/bin/sh

flask db upgrade
gunicorn -w 4 --reload ai_medit:app -b 0.0.0.0:5000 --timeout 480