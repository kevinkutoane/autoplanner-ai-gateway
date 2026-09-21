"""Strongly-typed AI operations supported by AutoPlanner Gateway."""

from enum import Enum
from typing import Optional


class AIOperation(str, Enum):
    """Semantic operations matching the Flutter client's AIOperation enum."""

    BRAIN_DUMP = "brain_dump"
    PARSE_TASKS = "parse_tasks"
    PLAN_DAY = "plan_day"
    CHAT_COACH = "chat_coach"
    DAILY_INSIGHT = "daily_insight"
    SUGGEST_RESCHEDULE = "suggest_reschedule"
    SUMMARIZE_NOTE = "summarize_note"
    GENERATE_TAGS = "generate_tags"
    EXTRACT_MEMORY = "extract_memory"
    EXTRACT_PATTERNS = "extract_patterns"
    SUGGEST_TASKS = "suggest_tasks"
    WEEKLY_REVIEW = "weekly_review"
    PARSE_SCHEDULE_COMMAND = "parse_schedule_command"

    @classmethod
    def from_str(cls, value: Optional[str]) -> Optional["AIOperation"]:
        """Safely parse operation string case-insensitively or return None."""
        if not value:
            return None
        clean = value.strip().lower()
        for op in cls:
            if op.value == clean:
                return op
        return None

    @property
    def is_structured_json(self) -> bool:
        """Indicates whether this operation expects a structured JSON model response."""
        return self in {
            AIOperation.BRAIN_DUMP,
            AIOperation.PARSE_TASKS,
            AIOperation.PLAN_DAY,
            AIOperation.GENERATE_TAGS,
            AIOperation.EXTRACT_PATTERNS,
            AIOperation.SUGGEST_TASKS,
            AIOperation.PARSE_SCHEDULE_COMMAND,
        }
