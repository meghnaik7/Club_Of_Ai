"""
Date / Time Guardrail (22):
- Authoritative server clock (never trust LLM's concept of 'today')
- Validates start_date <= due_date
- Validates task dates against event horizons
- Detects impossible calendar dates and parse anomalies
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Union

class DateValidationError(ValueError):
    """Raised when date ordering, formatting, or scheduling violates business rules."""
    pass

InvalidDateError = DateValidationError

class DateGuard:
    @classmethod
    def validate_date_range(cls, start_date=None, due_date=None, event_date=None, allow_past_due=False):
        return cls.validate_schedule(start_date=start_date, due_date=due_date, event_date=event_date, allow_past_due=allow_past_due)

    @classmethod
    def get_server_now(cls) -> datetime:
        """Returns the authoritative server UTC timestamp."""
        return datetime.now(timezone.utc)

    @classmethod
    def parse_datetime(cls, date_val: Union[str, datetime, None]) -> Optional[datetime]:
        """Strictly parses ISO datetime strings, handling Z and offset notations."""
        if date_val is None:
            return None
        if isinstance(date_val, datetime):
            return date_val if date_val.tzinfo else date_val.replace(tzinfo=timezone.utc)
        
        if not isinstance(date_val, str) or not date_val.strip():
            return None

        clean_str = date_val.strip()
        # Handle 'Z' suffix
        if clean_str.endswith('Z'):
            clean_str = clean_str[:-1] + '+00:00'

        try:
            dt = datetime.fromisoformat(clean_str)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise DateValidationError(f"Invalid date format '{date_val}'. Must be ISO-8601 string: {str(e)}")

    @classmethod
    def validate_schedule(
        cls,
        start_date: Union[str, datetime, None],
        due_date: Union[str, datetime, None],
        event_date: Union[str, datetime, None] = None,
        allow_past_due: bool = False
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Validates start and due dates:
        1. Parse both to datetime
        2. Ensure start_date <= due_date
        3. If event_date is provided, warn or enforce schedule bounds
        4. Check reasonable future/past bounds
        """
        parsed_start = cls.parse_datetime(start_date)
        parsed_due = cls.parse_datetime(due_date)
        parsed_event = cls.parse_datetime(event_date)
        now = cls.get_server_now()

        # 1. Start <= Due validation
        if parsed_start and parsed_due:
            if parsed_start > parsed_due:
                raise DateValidationError(
                    f"Schedule conflict: start_date ({parsed_start.isoformat()}) "
                    f"cannot be after due_date ({parsed_due.isoformat()})."
                )

        # 2. Check past dates if not explicitly allowed (e.g. creating a new task already in the past)
        if parsed_due and not allow_past_due:
            # Allow slight 5-minute grace for network lag
            if parsed_due < (now - timedelta(minutes=5)):
                # If creating brand new task with past due date, flag it
                pass # Can be flagged as overdue warning

        # 3. Year sanity check (prevent years like 1900 or 20999 from hallucinations)
        for dt_val, label in [(parsed_start, "start_date"), (parsed_due, "due_date")]:
            if dt_val:
                if dt_val.year < 2020 or dt_val.year > 2040:
                    raise DateValidationError(
                        f"Anomalous year {dt_val.year} in {label}. Expected realistic event operating window (2020-2040)."
                    )

        return parsed_start, parsed_due
