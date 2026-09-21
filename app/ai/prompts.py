"""Server-owned prompt registry with versioned templates for all 13 semantic operations."""

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from app.ai.operations import AIOperation


@dataclass(frozen=True)
class OperationPrompt:
    """Represents a versioned server-side prompt template."""

    operation: AIOperation
    version: str
    system_instruction: str
    builder: Callable[[Dict[str, Any], Dict[str, Any]], str]
    is_json: bool = False

    def build_prompt(self, input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
        return self.builder(input_data, context_data)


def _build_parse_tasks(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    text = input_data.get("text") or input_data.get("rawInput") or input_data.get("content") or ""
    memories = context_data.get("memories") or []
    mem_str = f"\nRelevant user habits/memories: {json.dumps(memories)}" if memories else ""
    return (
        f"Extract all actionable tasks from the following text into a JSON array.\n"
        f"Input text:\n\"\"\"{text}\"\"\"{mem_str}\n\n"
        f"Respond ONLY with a JSON array where each element has:\n"
        f"- 'title': task title (string)\n"
        f"- 'startTime': 'HH:MM' if mentioned, else null\n"
        f"- 'estimatedMinutes': integer estimate (default 30 if unspecified)\n"
        f"- 'priority': integer 0 (low), 1 (medium), 2 (high), 3 (urgent)\n"
        f"- 'tags': list of string tags"
    )


def _build_brain_dump(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    text = input_data.get("text") or input_data.get("rawInput") or ""
    start_time = context_data.get("suggestedStartTime") or ""
    time_hint = f"\nReference start time: {start_time}" if start_time else ""
    return (
        f"Parse this stream-of-consciousness brain dump into structured components:{time_hint}\n"
        f"Input:\n\"\"\"{text}\"\"\"\n\n"
        f"Respond ONLY with a JSON object containing:\n"
        f"- 'tasks': array of actionable items with 'title', 'estimatedMinutes', 'priority'\n"
        f"- 'notes': array of information/ideas with 'title', 'content'\n"
        f"- 'goals': array of desired outcomes with 'title'\n"
        f"- 'memories': array of preferences or habits with 'content'"
    )


def _build_plan_day(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    tasks = context_data.get("existingTasks") or []
    work_start = context_data.get("workStartHour", 9)
    work_hours = context_data.get("workHoursPerDay", 8)
    additional = input_data.get("additionalInput") or ""
    return (
        f"Plan and sequence the user's daily tasks.\n"
        f"Working window: start hour {work_start}:00, duration {work_hours} hours.\n"
        f"Tasks to schedule: {json.dumps(tasks)}\n"
        f"Additional notes: {additional}\n\n"
        f"Respond ONLY with a JSON array of scheduled/prioritized task objects with:\n"
        f"- 'id': original task ID\n"
        f"- 'title': task title\n"
        f"- 'estimatedMinutes': calibrated duration in minutes\n"
        f"- 'priority': calibrated priority 0-3\n"
        f"- 'tags': list of category tags"
    )


def _build_chat_coach(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    message = input_data.get("message") or ""
    history = input_data.get("history") or []
    hist_str = "\n".join([f"{h.get('role', 'user')}: {h.get('text', '')}" for h in history])
    return (
        f"Previous conversation:\n{hist_str}\n\n"
        f"User message: {message}\n\n"
        f"Provide supportive, actionable, concise productivity coaching in 2-4 sentences."
    )


def _build_daily_insight(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    tasks = context_data.get("tasks") or []
    goals = context_data.get("goals") or []
    memories = context_data.get("memories") or []
    return (
        f"Generate an energizing, concise morning productivity insight (1-2 sentences) based on:\n"
        f"Tasks today: {len(tasks)}\n"
        f"Active goals: {json.dumps(goals)}\n"
        f"User memories: {json.dumps(memories)}"
    )


def _build_suggest_reschedule(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    title = input_data.get("taskTitle") or "Task"
    duration = input_data.get("durationMinutes", 30)
    slots = context_data.get("slots") or context_data.get("candidateSlots") or []
    return (
        f"Select the best candidate slot index for the overdue/unplaced task:\n"
        f"Task: '{title}' ({duration} minutes)\n"
        f"Available candidate slots: {json.dumps(slots)}\n\n"
        f"Respond ONLY with the zero-based index integer of the single best slot (e.g. 0, 1, 2)."
    )


def _build_summarize_note(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    content = input_data.get("content") or ""
    return (
        f"Provide a crisp, clear 1-2 sentence executive summary of this note:\n"
        f"\"\"\"{content}\"\"\""
    )


def _build_generate_tags(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    content = input_data.get("content") or ""
    return (
        f"Suggest 2 to 5 relevant, lowercase topical tags for this content.\n"
        f"Content:\n\"\"\"{content}\"\"\"\n\n"
        f"Respond ONLY with a JSON array of lowercase strings, e.g. [\"planning\", \"finance\"]."
    )


def _build_extract_memory(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    ctx = input_data.get("context") or ""
    source_type = input_data.get("sourceType") or "user"
    return (
        f"Extract a single reusable, permanent long-term user preference or productivity habit.\n"
        f"Source: {source_type}\n"
        f"Context:\n\"\"\"{ctx}\"\"\"\n\n"
        f"Return ONLY the concise insight string (or empty string if nothing permanent is learned)."
    )


def _build_extract_patterns(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    history = context_data.get("completedHistory") or context_data.get("completedTasks") or []
    count = context_data.get("completedCount", len(history))
    return (
        f"Analyze these {count} completed tasks for recurring productivity patterns and rhythms:\n"
        f"{json.dumps(history)}\n\n"
        f"Respond ONLY with a JSON array of pattern objects with:\n"
        f"- 'pattern': description of observed habit (string)\n"
        f"- 'confidence': float between 0.0 and 1.0\n"
        f"- 'category': 'time' | 'category' | 'duration'"
    )


def _build_suggest_tasks(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    day_name = input_data.get("dayName") or "Today"
    memories = context_data.get("memories") or []
    return (
        f"Suggest 2-4 context-appropriate tasks for {day_name} based on user habits:\n"
        f"User habits: {json.dumps(memories)}\n\n"
        f"Respond ONLY with a JSON array of task title strings."
    )


def _build_weekly_review(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    tasks_count = input_data.get("tasksCount", 0)
    completed_count = input_data.get("completedCount", 0)
    rate = input_data.get("completionRate", 0.0)
    goals = context_data.get("goals") or []
    return (
        f"Generate a structured weekly review synthesis.\n"
        f"Total tasks: {tasks_count}, Completed: {completed_count}, Completion rate: {rate*100:.0f}%\n"
        f"Active goals: {json.dumps(goals)}\n\n"
        f"Format with markdown headings: ## Highlights, ## Wins, and ## Next Week Focus."
    )


def _build_parse_schedule_command(input_data: Dict[str, Any], context_data: Dict[str, Any]) -> str:
    query = input_data.get("query") or ""
    ref_time = input_data.get("referenceTime") or ""
    return (
        f"Parse this schedule modification command into a structured action.\n"
        f"Command: \"\"\"{query}\"\"\"\n"
        f"Reference time: {ref_time}\n\n"
        f"Respond ONLY with a JSON object containing:\n"
        f"- 'action': 'shift' | 'fit' | 'focus' | 'clear'\n"
        f"- 'minutes': integer duration or offset\n"
        f"- 'explanation': brief natural language explanation"
    )


class PromptRegistry:
    """Authoritative server-owned registry of prompt templates for all semantic operations."""

    _REGISTRY: Dict[AIOperation, OperationPrompt] = {
        AIOperation.PARSE_TASKS: OperationPrompt(
            operation=AIOperation.PARSE_TASKS,
            version="parse_tasks:v1",
            system_instruction="You are an expert task parsing engine for AutoPlanner. Extract actionable tasks accurately.",
            builder=_build_parse_tasks,
            is_json=True,
        ),
        AIOperation.BRAIN_DUMP: OperationPrompt(
            operation=AIOperation.BRAIN_DUMP,
            version="brain_dump:v1",
            system_instruction="You are AutoPlanner's brain dump decomposition engine. Classify thoughts into tasks, notes, goals, and memories.",
            builder=_build_brain_dump,
            is_json=True,
        ),
        AIOperation.PLAN_DAY: OperationPrompt(
            operation=AIOperation.PLAN_DAY,
            version="plan_day:v1",
            system_instruction="You are AutoPlanner's intelligent daily sequencing engine. Optimize realistic task durations and priorities.",
            builder=_build_plan_day,
            is_json=True,
        ),
        AIOperation.CHAT_COACH: OperationPrompt(
            operation=AIOperation.CHAT_COACH,
            version="chat_coach:v1",
            system_instruction="You are the empathetic, encouraging, and highly practical AutoPlanner AI Productivity Coach.",
            builder=_build_chat_coach,
            is_json=False,
        ),
        AIOperation.DAILY_INSIGHT: OperationPrompt(
            operation=AIOperation.DAILY_INSIGHT,
            version="daily_insight:v1",
            system_instruction="You provide concise, high-impact daily morning productivity briefings.",
            builder=_build_daily_insight,
            is_json=False,
        ),
        AIOperation.SUGGEST_RESCHEDULE: OperationPrompt(
            operation=AIOperation.SUGGEST_RESCHEDULE,
            version="suggest_reschedule:v1",
            system_instruction="You determine the optimal rescheduling slot for interrupted or overdue tasks.",
            builder=_build_suggest_reschedule,
            is_json=False,
        ),
        AIOperation.SUMMARIZE_NOTE: OperationPrompt(
            operation=AIOperation.SUMMARIZE_NOTE,
            version="summarize_note:v1",
            system_instruction="You produce clear, concise 1-2 sentence summaries of user notes.",
            builder=_build_summarize_note,
            is_json=False,
        ),
        AIOperation.GENERATE_TAGS: OperationPrompt(
            operation=AIOperation.GENERATE_TAGS,
            version="generate_tags:v1",
            system_instruction="You extract 2-5 lowercase organizational tags for tasks and notes.",
            builder=_build_generate_tags,
            is_json=True,
        ),
        AIOperation.EXTRACT_MEMORY: OperationPrompt(
            operation=AIOperation.EXTRACT_MEMORY,
            version="extract_memory:v1",
            system_instruction="You extract enduring user preferences and habits into concise memory facts.",
            builder=_build_extract_memory,
            is_json=False,
        ),
        AIOperation.EXTRACT_PATTERNS: OperationPrompt(
            operation=AIOperation.EXTRACT_PATTERNS,
            version="extract_patterns:v1",
            system_instruction="You identify statistical patterns and productivity rhythms from completed tasks.",
            builder=_build_extract_patterns,
            is_json=True,
        ),
        AIOperation.SUGGEST_TASKS: OperationPrompt(
            operation=AIOperation.SUGGEST_TASKS,
            version="suggest_tasks:v1",
            system_instruction="You suggest proactive, context-aware tasks based on user history.",
            builder=_build_suggest_tasks,
            is_json=True,
        ),
        AIOperation.WEEKLY_REVIEW: OperationPrompt(
            operation=AIOperation.WEEKLY_REVIEW,
            version="weekly_review:v1",
            system_instruction="You synthesize comprehensive weekly productivity reviews.",
            builder=_build_weekly_review,
            is_json=False,
        ),
        AIOperation.PARSE_SCHEDULE_COMMAND: OperationPrompt(
            operation=AIOperation.PARSE_SCHEDULE_COMMAND,
            version="parse_schedule_command:v1",
            system_instruction="You parse natural language commands that manipulate the schedule.",
            builder=_build_parse_schedule_command,
            is_json=True,
        ),
    }

    @classmethod
    def get(cls, operation: AIOperation) -> OperationPrompt:
        """Retrieves the authoritative versioned prompt template for an operation."""
        if operation not in cls._REGISTRY:
            raise KeyError(f"No prompt template registered for operation: {operation}")
        return cls._REGISTRY[operation]

    @classmethod
    def all_operations(cls) -> list[AIOperation]:
        return list(cls._REGISTRY.keys())
