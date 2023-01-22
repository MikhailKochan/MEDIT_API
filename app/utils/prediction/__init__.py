from flask import Blueprint

bp = Blueprint("make_predict", __name__)

from . import make_predict
