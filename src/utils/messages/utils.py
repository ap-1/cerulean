def render_progress_bar(current: int, total: int, bar_length: int = 20) -> str:
    if total == 0:
        return "[no progress info]"

    percent = current / total
    filled = int(bar_length * percent)
    bar = "█" * filled + "░" * (bar_length - filled)
    return f"[{bar}] {int(percent * 100)}%"
