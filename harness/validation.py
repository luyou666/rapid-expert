from __future__ import annotations


REQUIRED_TASK_FIELDS = ("domain", "goal")
STRING_LIMITS = {
    "domain": 120,
    "goal": 4000,
    "question": 4000,
    "user_level": 120,
    "daily_time": 120,
    "region": 120,
    "time_range": 120,
    "github_query": 300,
}


def validate_task(task: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(task, dict):
        return ["task must be a JSON object."]
    for field in REQUIRED_TASK_FIELDS:
        if not isinstance(task.get(field), str) or not task.get(field, "").strip():
            errors.append(f"{field} is required and must be a non-empty string.")
    for field, max_length in STRING_LIMITS.items():
        if field in task and not isinstance(task[field], str):
            errors.append(f"{field} must be a string.")
            continue
        if isinstance(task.get(field), str) and len(task[field]) > max_length:
            errors.append(f"{field} must be at most {max_length} characters.")
    if "no_network" in task and not isinstance(task["no_network"], bool):
        errors.append("no_network must be a boolean.")
    if "approved_tools" in task:
        errors.append("approved_tools is internal approval state and cannot be supplied in task input.")
    for field in ("min_stars", "github_limit"):
        if field in task and (not isinstance(task[field], int) or task[field] < 0):
            errors.append(f"{field} must be a non-negative integer.")
    return errors
