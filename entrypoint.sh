#!/bin/sh

flask db upgrade
gunicorn --reload ai_medit:app -b 0.0.0.0:5000