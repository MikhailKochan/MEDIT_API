from flask import Blueprint

bp = Blueprint("cutting_svs", __name__)

from . import cutting_svs
