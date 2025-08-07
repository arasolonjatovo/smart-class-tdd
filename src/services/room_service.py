from sqlalchemy import text
from src.database import get_session


class RoomService:
    """Service for handling room-related database operations"""
    
    @staticmethod
    def get_all_rooms() -> list[dict]:
        """
        Get all available rooms from database with equipment information.
        
        Returns:
            List of room dictionaries with equipment counts
        """
        with get_session() as session:
            query = text(
                """
                SELECT 
                    r.id,
                    r.name,
                    r.capacity,
                    r.building,
                    r.floor,
                    r.is_enabled,
                    COUNT(DISTINCT e.id) FILTER (WHERE e.type = 'ac' AND e.is_functional = true) as ac_count,
                    COUNT(DISTINCT e.id) FILTER (WHERE e.type = 'heater' AND e.is_functional = true) as heater_count
                FROM room r
                LEFT JOIN equipment e ON r.id = e.room_id
                WHERE r.is_enabled = true
                GROUP BY r.id, r.name, r.capacity, r.building, r.floor, r.is_enabled
                ORDER BY r.building, r.floor, r.name
            """
            )

            result = session.execute(query)

            rooms = []
            for row in result:
                room = {
                    "id": str(row.id),
                    "name": row.name,
                    "capacity": row.capacity,
                    "building": row.building,
                    "floor": row.floor,
                    "hasAC": row.ac_count > 0,
                    "hasHeater": row.heater_count > 0,
                }
                rooms.append(room)

            return rooms