from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from sqlalchemy import text
from src.database.connection import get_session

logger = logging.getLogger(__name__)


class SensorDataService:
    """Service for retrieving sensor data from the database"""

    @staticmethod
    def get_latest_room_data(
        room_id: str, before_datetime: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get the latest sensor data for a room before a specific datetime

        Args:
            room_id: UUID of the room
            before_datetime: Get data before this datetime (defaults to now)

        Returns:
            Dictionary with temperature, humidity, and air pressure data
        """
        if before_datetime is None:
            before_datetime = datetime.now()

        with get_session() as session:
            try:
                temp_query = text(
                    """
                    SELECT CAST(data AS FLOAT) as temperature, saved_at
                    FROM temperature
                    WHERE room_id = :room_id AND saved_at < :before_datetime
                    ORDER BY saved_at DESC
                    LIMIT 1
                """
                )
                temp_result = session.execute(
                    temp_query, {"room_id": room_id, "before_datetime": before_datetime}
                ).fetchone()

                humidity_query = text(
                    """
                    SELECT CAST(data AS FLOAT) as humidity, saved_at
                    FROM humidity
                    WHERE room_id = :room_id AND saved_at < :before_datetime
                    ORDER BY saved_at DESC
                    LIMIT 1
                """
                )
                humidity_result = session.execute(
                    humidity_query,
                    {"room_id": room_id, "before_datetime": before_datetime},
                ).fetchone()

                pressure_query = text(
                    """
                    SELECT CAST(data AS FLOAT) as pressure, saved_at
                    FROM pressure
                    WHERE room_id = :room_id AND saved_at < :before_datetime
                    ORDER BY saved_at DESC
                    LIMIT 1
                """
                )
                pressure_result = session.execute(
                    pressure_query,
                    {"room_id": room_id, "before_datetime": before_datetime},
                ).fetchone()

                result = {
                    "temperature": temp_result.temperature if temp_result else 21.0,
                    "humidity": humidity_result.humidity if humidity_result else 50.0,
                    "airPressure": (
                        pressure_result.pressure if pressure_result else 1013.0
                    ),
                    "temperature_saved_at": (
                        temp_result.saved_at if temp_result else None
                    ),
                    "humidity_saved_at": (
                        humidity_result.saved_at if humidity_result else None
                    ),
                    "pressure_saved_at": (
                        pressure_result.saved_at if pressure_result else None
                    ),
                }
                
                # Get outdoor temperature from weather table
                weather_query = text("""
                    SELECT (temperature_min + temperature_max) / 2.0 as avg_temp
                    FROM weather
                    WHERE date = :target_date
                    ORDER BY fetched_at DESC
                    LIMIT 1
                """)
                weather_result = session.execute(
                    weather_query,
                    {"target_date": before_datetime.date()}
                ).fetchone()
                
                result["temperature_outdoor"] = weather_result.avg_temp if weather_result else 15.0

                return result

            except Exception as e:
                logger.error(f"Error retrieving sensor data for room {room_id}: {e}")
                return {
                    "temperature": 21.0,
                    "humidity": 50.0,
                    "airPressure": 1013.0,
                    "temperature_outdoor": 15.0,
                    "temperature_saved_at": None,
                    "humidity_saved_at": None,
                    "pressure_saved_at": None,
                }

    @staticmethod
    def get_room_data_for_hour(
        room_id: str, target_datetime: datetime
    ) -> Dict[str, Any]:
        """
        Get sensor data for a specific room at a specific hour

        Args:
            room_id: UUID of the room
            target_datetime: The datetime to get data for

        Returns:
            Dictionary with temperature, humidity, and air pressure data
        """
        hour_start = target_datetime.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)

        with get_session() as session:
            try:
                temp_query = text(
                    """
                    SELECT AVG(CAST(data AS FLOAT)) as avg_temperature,
                           MIN(CAST(data AS FLOAT)) as min_temperature,
                           MAX(CAST(data AS FLOAT)) as max_temperature
                    FROM temperature
                    WHERE room_id = :room_id 
                    AND saved_at >= :hour_start 
                    AND saved_at < :hour_end
                """
                )
                temp_result = session.execute(
                    temp_query,
                    {
                        "room_id": room_id,
                        "hour_start": hour_start,
                        "hour_end": hour_end,
                    },
                ).fetchone()

                humidity_query = text(
                    """
                    SELECT AVG(CAST(data AS FLOAT)) as avg_humidity
                    FROM humidity
                    WHERE room_id = :room_id 
                    AND saved_at >= :hour_start 
                    AND saved_at < :hour_end
                """
                )
                humidity_result = session.execute(
                    humidity_query,
                    {
                        "room_id": room_id,
                        "hour_start": hour_start,
                        "hour_end": hour_end,
                    },
                ).fetchone()

                pressure_query = text(
                    """
                    SELECT AVG(CAST(data AS FLOAT)) as avg_pressure
                    FROM pressure
                    WHERE room_id = :room_id 
                    AND saved_at >= :hour_start 
                    AND saved_at < :hour_end
                """
                )
                pressure_result = session.execute(
                    pressure_query,
                    {
                        "room_id": room_id,
                        "hour_start": hour_start,
                        "hour_end": hour_end,
                    },
                ).fetchone()

                if not temp_result or temp_result.avg_temperature is None:
                    return SensorDataService.get_latest_room_data(room_id, hour_start)

                return {
                    "temperature": (
                        float(temp_result.avg_temperature)
                        if temp_result.avg_temperature
                        else 21.0
                    ),
                    "humidity": (
                        float(humidity_result.avg_humidity)
                        if humidity_result and humidity_result.avg_humidity
                        else 50.0
                    ),
                    "airPressure": (
                        float(pressure_result.avg_pressure)
                        if pressure_result and pressure_result.avg_pressure
                        else 1013.0
                    ),
                    "min_temperature": (
                        float(temp_result.min_temperature)
                        if temp_result.min_temperature
                        else None
                    ),
                    "max_temperature": (
                        float(temp_result.max_temperature)
                        if temp_result.max_temperature
                        else None
                    ),
                }

            except Exception as e:
                logger.error(
                    f"Error retrieving hourly sensor data for room {room_id}: {e}"
                )
                return SensorDataService.get_latest_room_data(room_id, target_datetime)
