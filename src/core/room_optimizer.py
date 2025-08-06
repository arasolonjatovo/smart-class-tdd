from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import logging
import os
import joblib
import pandas as pd
from src.predict_temperature import predict_remaining_day_structured
from src.services.sensor_data_service import SensorDataService

logger = logging.getLogger(__name__)


class RoomOptimizer:
    def __init__(self, rooms, lessons, preferences=None):
        """
        Initialize the room optimizer with constraint programming

        Args:
            rooms: List of available rooms with their properties
            lessons: List of lessons that need room assignments
            preferences: Dictionary with optimization preferences (weights)
        """
        self.rooms = rooms
        self.lessons = lessons
        self.preferences = preferences or {
            "temperature_weight": 0.3,
            "equipment_weight": 0.2,
            "capacity_weight": 0.5,
        }
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.temperature_predictions = {}
        self.seven_days_from_now = datetime.now() + timedelta(days=7)

    def optimize(self):
        """Run the optimization to find optimal room assignments"""
        if not self.lessons:
            return self._format_empty_result()

        self._calculate_all_temperature_predictions()

        assignments = self._create_assignment_variables()

        self._add_capacity_constraints(assignments)
        self._add_no_overlap_constraints(assignments)

        objective_terms = []
        objective_terms.extend(self._add_capacity_fit_objective(assignments))
        objective_terms.extend(self._add_equipment_objective(assignments))
        objective_terms.extend(self._add_temperature_objective(assignments))

        # Maximize the total score
        self.model.Maximize(sum(objective_terms))

        # Solve the model
        status = self.solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            return self._extract_solution(assignments, status)
        else:
            logger.warning(f"No feasible solution found. Status: {status}")
            return self._format_infeasible_result()

    def _create_assignment_variables(self):
        """Create boolean variables for each possible lesson-room assignment"""
        assignments = {}

        for i, lesson in enumerate(self.lessons):
            for j, room in enumerate(self.rooms):
                var_name = f"lesson_{i}_room_{j}"
                assignments[(i, j)] = self.model.NewBoolVar(var_name)

        return assignments

    def _add_capacity_constraints(self, assignments):
        """Hard constraint: Room capacity must be >= class size"""
        for i, lesson in enumerate(self.lessons):
            valid_rooms = []
            student_count = lesson.get("student_count", 0)

            for j, room in enumerate(self.rooms):
                if room["capacity"] >= student_count:
                    valid_rooms.append(assignments[(i, j)])
                else:
                    self.model.Add(assignments[(i, j)] == 0)

            if valid_rooms:
                self.model.AddExactlyOne(valid_rooms)
            else:
                logger.warning(
                    f"No room has sufficient capacity for lesson {lesson['title']} "
                    f"(needs {student_count} seats)"
                )

    def _add_no_overlap_constraints(self, assignments):
        """Hard constraint: No two lessons can use the same room at the same time"""
        # Convert lesson times to intervals
        lesson_intervals = []
        for lesson in self.lessons:
            start = datetime.fromisoformat(lesson["start_time"])
            end = datetime.fromisoformat(lesson["end_time"])
            lesson_intervals.append((start, end))

        for j, room in enumerate(self.rooms):
            for i1, (start1, end1) in enumerate(lesson_intervals):
                for i2, (start2, end2) in enumerate(lesson_intervals):
                    if i1 < i2:
                        if start1 < end2 and start2 < end1:
                            self.model.Add(
                                assignments[(i1, j)] + assignments[(i2, j)] <= 1
                            )

    def _add_capacity_fit_objective(self, assignments):
        """Soft constraint: Prefer rooms with capacity close to class size"""
        objective_terms = []

        for i, lesson in enumerate(self.lessons):
            student_count = lesson.get("student_count", 0)
            for j, room in enumerate(self.rooms):
                if room["capacity"] >= student_count:
                    capacity_ratio = (
                        student_count / room["capacity"] if room["capacity"] > 0 else 0
                    )
                    score = int(
                        capacity_ratio * 100 * self.preferences["capacity_weight"]
                    )
                    objective_terms.append(score * assignments[(i, j)])

        return objective_terms

    def _add_equipment_objective(self, assignments):
        """Soft constraint: Prefer rooms with temperature-appropriate equipment"""
        objective_terms = []

        for i, lesson in enumerate(self.lessons):
            lesson_datetime = datetime.fromisoformat(
                lesson["start_time"].replace("Z", "+00:00")
            )

            for j, room in enumerate(self.rooms):
                equipment_score = 0

                # For lessons beyond 7 days, use static equipment scoring
                if lesson_datetime > self.seven_days_from_now:
                    if room.get("hasAC", False):
                        equipment_score += 20
                    if room.get("hasHeater", False):
                        equipment_score += 20
                else:
                    predicted_temp = self.temperature_predictions.get((i, j), 21.0)

                    if room.get("hasAC", False):
                        if predicted_temp > 25:
                            equipment_score += 50
                        elif predicted_temp > 23:
                            equipment_score += 30
                        elif predicted_temp > 21:
                            equipment_score += 10

                    if room.get("hasHeater", False):
                        if predicted_temp < 17:
                            equipment_score += 50
                        elif predicted_temp < 19:
                            equipment_score += 30
                        elif predicted_temp < 21:
                            equipment_score += 10

                weighted_score = int(
                    equipment_score * self.preferences["equipment_weight"]
                )
                objective_terms.append(weighted_score * assignments[(i, j)])

        return objective_terms

    def _calculate_all_temperature_predictions(self):
        """Pre-calculate temperature predictions for all room-lesson combinations"""
        model = None
        try:
            model_path = os.path.join(
                os.path.dirname(__file__), "../../model/random_forest.pkl"
            )
            model = joblib.load(model_path)
            logger.info("Temperature prediction model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load temperature model: {e}")
            return

        for i, lesson in enumerate(self.lessons):
            lesson_datetime = datetime.fromisoformat(
                lesson["start_time"].replace("Z", "+00:00")
            )

            if lesson_datetime > self.seven_days_from_now:
                for j in range(len(self.rooms)):
                    self.temperature_predictions[(i, j)] = 21.0
                continue

            day_name = lesson_datetime.strftime("%A").lower()

            for j, room in enumerate(self.rooms):
                try:
                    student_count = lesson.get("student_count", 0)
                    room_capacity = room.get("capacity", 1)
                    capacity_percentage = (
                        (student_count / room_capacity) * 100
                        if room_capacity > 0
                        else 0
                    )

                    sensor_data = SensorDataService.get_latest_room_data(
                        room["id"], lesson_datetime
                    )

                    if sensor_data.get("temperature_saved_at"):
                        last_data_hour = sensor_data["temperature_saved_at"].strftime(
                            "%H:00"
                        )
                    else:
                        last_data_hour = "09:00"

                    initial_data = pd.DataFrame(
                        {
                            "room": [room["name"]],
                            "day": [day_name],
                            "hour": [last_data_hour],
                            "temperature": [sensor_data["temperature"]],
                            "humidity": [sensor_data["humidity"]],
                            "airPressure": [sensor_data["airPressure"]],
                            "capacity_percentage": [capacity_percentage],
                            "temperature_outdoor": [sensor_data["temperature_outdoor"]],
                        }
                    )

                    predictions = predict_remaining_day_structured(
                        room["name"], day_name, last_data_hour, model, initial_data
                    )

                    lesson_end_datetime = datetime.fromisoformat(
                        lesson["end_time"].replace("Z", "+00:00")
                    )

                    temperatures = []
                    current_hour = lesson_datetime.replace(
                        minute=0, second=0, microsecond=0
                    )
                    end_hour = lesson_end_datetime.replace(
                        minute=0, second=0, microsecond=0
                    )

                    while current_hour <= end_hour:
                        hour_str = current_hour.strftime("%H:00")
                        if (
                            hour_str
                            in predictions["room"]["days"][day_name]["temperature"]
                        ):
                            temperatures.append(
                                predictions["room"]["days"][day_name]["temperature"][
                                    hour_str
                                ]
                            )
                        current_hour = current_hour + timedelta(hours=1)

                    if temperatures:
                        predicted_temp = sum(temperatures) / len(temperatures)
                        self.temperature_predictions[(i, j)] = predicted_temp
                    else:
                        self.temperature_predictions[(i, j)] = 21.0  # Default

                except Exception as e:
                    logger.warning(
                        f"Temperature prediction failed for room {room['name']}, lesson {i}: {e}"
                    )
                    self.temperature_predictions[(i, j)] = 21.0  # Default

    def _add_temperature_objective(self, assignments):
        """Soft constraint: Prefer rooms with comfortable temperature predictions"""
        objective_terms = []

        for i, lesson in enumerate(self.lessons):
            for j, room in enumerate(self.rooms):
                predicted_temp = self.temperature_predictions.get((i, j), 21.0)

                if 20 <= predicted_temp <= 22:
                    temp_score = 100
                elif 19 <= predicted_temp <= 23:
                    temp_score = 90
                elif 18 <= predicted_temp <= 24:
                    temp_score = 70
                elif 17 <= predicted_temp <= 25:
                    temp_score = 50
                else:
                    temp_score = max(0, 30 - abs(predicted_temp - 21) * 5)

                weighted_score = int(
                    temp_score * self.preferences["temperature_weight"]
                )
                objective_terms.append(weighted_score * assignments[(i, j)])

        return objective_terms

    def _extract_solution(self, assignments, status):
        """Extract the optimized room assignments from the solver"""
        optimized_assignments = []

        for i, lesson in enumerate(self.lessons):
            assigned_room = None

            for j, room in enumerate(self.rooms):
                if self.solver.Value(assignments[(i, j)]) == 1:
                    assigned_room = room
                    break

            if assigned_room:
                student_count = lesson.get("student_count", 0)
                capacity_fit = (
                    min(student_count / assigned_room["capacity"], 1.0)
                    if assigned_room["capacity"] > 0
                    else 0
                )
                equipment_score = 0.5
                if assigned_room.get("hasAC", False):
                    equipment_score += 0.25
                if assigned_room.get("hasHeater", False):
                    equipment_score += 0.25

                optimized_assignments.append(
                    {
                        "lesson": lesson,
                        "assigned_room": assigned_room,
                        "scores": {
                            "capacity_fit": round(capacity_fit, 3),
                            "equipment": round(equipment_score, 3),
                            "temperature": 0.8,  # Mock for now
                            "overall": round(
                                capacity_fit * self.preferences["capacity_weight"]
                                + equipment_score * self.preferences["equipment_weight"]
                                + 0.8 * self.preferences["temperature_weight"],
                                3,
                            ),
                        },
                    }
                )
            else:
                logger.warning(f"No room assigned for lesson {lesson['title']}")

        return {
            "status": "optimal" if status == cp_model.OPTIMAL else "feasible",
            "assignments": optimized_assignments,
            "solver_stats": {
                "conflicts": self.solver.NumConflicts(),
                "branches": self.solver.NumBranches(),
                "wall_time": self.solver.WallTime(),
            },
        }

    def _format_empty_result(self):
        """Format result when there are no lessons to optimize"""
        return {
            "status": "empty",
            "assignments": [],
            "message": "No lessons to optimize",
        }

    def _format_infeasible_result(self):
        """Format result when no feasible solution exists"""
        return {
            "status": "infeasible",
            "assignments": [],
            "message": "No feasible room assignment found. Check constraints.",
            "solver_stats": {
                "conflicts": self.solver.NumConflicts(),
                "branches": self.solver.NumBranches(),
                "wall_time": self.solver.WallTime(),
            },
        }
