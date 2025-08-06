from flask import Blueprint, request, jsonify
from datetime import datetime
from src.core.room_optimizer import RoomOptimizer
from src.services.lesson_service import LessonService
from src.services.room_service import RoomService

optimization_bp = Blueprint("optimization", __name__)


@optimization_bp.route("/weekly-planning", methods=["POST"])
def optimize_weekly_planning():
    """Optimize room assignments for weekly planning and save to database"""
    try:
        data = request.get_json()

        if "start_date" in data and "end_date" in data:
            start_date = datetime.fromisoformat(data["start_date"])
            end_date = datetime.fromisoformat(data["end_date"])
        else:
            return (
                jsonify(
                    {"error": "Missing required fields: either (start_date, end_date)"}
                ),
                400,
            )

        preferences = data.get("preferences", {})

        lessons = LessonService.get_lessons_for_date_range(start_date, end_date)

        if not lessons:
            response_data = {
                "message": "No lessons found for the specified period",
                "dateRange": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            }

            return jsonify(response_data), 200

        rooms = RoomService.get_all_rooms()

        optimizer = RoomOptimizer(rooms, lessons, preferences)
        optimization_result = optimizer.optimize()

        if optimization_result["status"] in ["optimal", "feasible"]:
            # Update room assignments in database
            updated_count = 0
            for assignment in optimization_result["assignments"]:
                lesson = assignment["lesson"]
                room = assignment["assigned_room"]

                if LessonService.update_lesson_room(lesson["id"], room["id"]):
                    updated_count += 1

            response_data = {
                "message": "Room assignments optimized successfully",
                "status": optimization_result["status"],
                "lessonsOptimized": updated_count,
                "totalLessons": len(lessons),
                "dateRange": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "solverStats": optimization_result.get("solver_stats", {}),
                "timestamp": datetime.now().isoformat(),
            }

            return jsonify(response_data), 200

        else:
            response_data = {
                "message": "Optimization failed - no feasible solution found",
                "status": optimization_result["status"],
                "dateRange": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "solverStats": optimization_result.get("solver_stats", {}),
                "timestamp": datetime.now().isoformat(),
            }

            return jsonify(response_data), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500
