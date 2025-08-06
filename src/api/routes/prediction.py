from flask import Blueprint, request, jsonify
import random
from datetime import datetime

prediction_bp = Blueprint("prediction", __name__)


@prediction_bp.route("/room/<room_id>", methods=["GET"])
def predict_room_conditions(room_id):
    """Get predicted conditions for a specific room for the week"""
    try:
        response = {}

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
