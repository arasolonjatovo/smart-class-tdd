from datetime import datetime, timedelta


def get_week_dates(year: int, week_number: int) -> tuple[datetime, datetime]:
    """
    Get start and end dates for a given week number.
    
    Args:
        year: The year
        week_number: The ISO week number
        
    Returns:
        Tuple of (start_date, end_date) for the week
    """
    jan_first = datetime(year, 1, 1)
    days_to_week = (week_number - 1) * 7
    week_start = jan_first + timedelta(days=days_to_week - jan_first.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def parse_date_range(start_date_str: str, end_date_str: str) -> tuple[datetime, datetime]:
    """
    Parse date strings and return datetime objects with proper time boundaries.
    
    Args:
        start_date_str: Start date in ISO format (YYYY-MM-DD)
        end_date_str: End date in ISO format (YYYY-MM-DD)
        
    Returns:
        Tuple of (start_datetime, end_datetime) with times set to start/end of day
    """
    start_date = datetime.fromisoformat(start_date_str)
    end_date = datetime.fromisoformat(end_date_str)
    
    # Set time to start of day for start_date
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Set time to end of day for end_date
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_date, end_date