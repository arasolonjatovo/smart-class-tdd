from datetime import datetime
from sqlalchemy import text
from src.database import get_session
from src.utils.date_utils import get_week_dates


class LessonService:
    """Service for handling lesson-related database operations"""
    
    @staticmethod
    def get_lessons_for_date_range(start_date: datetime, end_date: datetime) -> list[dict]:
        """
        Retrieve lessons from database for a specific date range.
        
        Args:
            start_date: Start of the date range
            end_date: End of the date range
            
        Returns:
            List of lesson dictionaries with room and class information
        """
        with get_session() as session:
            query = text(
                """
                SELECT 
                    l.id,
                    l.title,
                    l.start_time,
                    l.end_time,
                    l.room_id,
                    l.class_id,
                    r.name as room_name,
                    r.capacity as room_capacity,
                    r.building,
                    r.floor,
                    c.name as class_name,
                    c.student_count,
                    CONCAT(u.first_name, ' ', u.last_name) as teacher_name
                FROM lesson l
                LEFT JOIN room r ON l.room_id = r.id
                JOIN class c ON l.class_id = c.id
                LEFT JOIN user_lesson ul ON l.id = ul.lesson_id
                LEFT JOIN "user" u ON ul.user_id = u.id
                WHERE l.start_time >= :start_date 
                AND l.start_time <= :end_date
                ORDER BY l.start_time
            """
            )

            result = session.execute(
                query, {"start_date": start_date, "end_date": end_date}
            )

            lessons = []
            for row in result:
                lesson = {
                    "id": str(row.id),
                    "title": row.title,
                    "start_time": row.start_time.isoformat(),
                    "end_time": row.end_time.isoformat(),
                    "room_id": str(row.room_id) if row.room_id else None,
                    "room_name": row.room_name if row.room_name else None,
                    "room_capacity": row.room_capacity if row.room_capacity else None,
                    "building": row.building if row.building else None,
                    "floor": row.floor if row.floor is not None else None,
                    "class_id": str(row.class_id),
                    "class_name": row.class_name,
                    "student_count": row.student_count,
                    "teacher_name": row.teacher_name or "TBD",
                }
                lessons.append(lesson)

            return lessons

    @classmethod
    def get_lessons_for_week(cls, year: int, week_number: int) -> list[dict]:
        """
        Retrieve lessons from database for a specific week.
        
        Args:
            year: The year
            week_number: The ISO week number
            
        Returns:
            List of lesson dictionaries
        """
        week_start, week_end = get_week_dates(year, week_number)
        return cls.get_lessons_for_date_range(week_start, week_end)

    @staticmethod
    def update_lesson_room(lesson_id: str, room_id: str) -> bool:
        """
        Update the room assignment for a lesson.
        
        Args:
            lesson_id: UUID of the lesson
            room_id: UUID of the new room
            
        Returns:
            True if update was successful, False otherwise
        """
        with get_session() as session:
            update_query = text(
                """
                UPDATE lesson 
                SET room_id = :room_id 
                WHERE id = :lesson_id
            """
            )
            
            result = session.execute(
                update_query, {"room_id": room_id, "lesson_id": lesson_id}
            )
            
            session.commit()
            return result.rowcount > 0