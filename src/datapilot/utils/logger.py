"""Logging utilities for the AI Planner Agent."""

from __future__ import annotations

import logging
import sys
from typing import Optional, Callable, Any

from datapilot.schema.models import AgentEvent, EventType


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    _enabled = True

    @classmethod
    def disable(cls) -> None:
        """Disable all colors (for non-TTY output)."""
        cls._enabled = False
        for attr in dir(cls):
            if not attr.startswith("_") and attr.isupper():
                setattr(cls, attr, "")

    @classmethod
    def enable(cls) -> None:
        """Re-enable colors."""
        if not cls._enabled:
            cls._enabled = True
            cls.RESET = "\033[0m"
            cls.BOLD = "\033[1m"
            cls.DIM = "\033[2m"
            cls.RED = "\033[31m"
            cls.GREEN = "\033[32m"
            cls.YELLOW = "\033[33m"
            cls.BLUE = "\033[34m"
            cls.MAGENTA = "\033[35m"
            cls.CYAN = "\033[36m"
            cls.WHITE = "\033[37m"
            cls.BRIGHT_RED = "\033[91m"
            cls.BRIGHT_GREEN = "\033[92m"
            cls.BRIGHT_YELLOW = "\033[93m"
            cls.BRIGHT_BLUE = "\033[94m"
            cls.BRIGHT_MAGENTA = "\033[95m"
            cls.BRIGHT_CYAN = "\033[96m"


# Auto-disable colors if not running in a TTY
if not sys.stdout.isatty():
    Colors.disable()


class AgentLogger:
    """Logger for the AI Planner Agent.

    Supports both console output (with colors) and event callbacks
    for streaming to a UI.

    Example:
        # Console-only logging
        logger = AgentLogger(name="planner")
        logger.info("Agent started")

        # With event callback for UI streaming
        def on_event(event: AgentEvent):
            send_to_websocket(event.to_sse())

        logger = AgentLogger(event_callback=on_event)
        logger.emit_event(EventType.AGENT_STARTED, message="Starting...")
    """

    def __init__(
        self,
        name: str = "datapilot",
        level: int = logging.INFO,
        event_callback: Optional[Callable[[AgentEvent], Any]] = None,
        verbose: bool = True,
    ) -> None:
        """Initialize the logger.

        Args:
            name: Logger name
            level: Logging level
            event_callback: Optional callback for streaming events to UI
            verbose: Whether to print to console
        """
        self.verbose = verbose
        self.event_callback = event_callback
        self._round_num = 0

        # Setup Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Add console handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def set_round(self, round_num: int) -> None:
        """Set the current round number for events."""
        self._round_num = round_num

    def info(self, message: str) -> None:
        """Log an info message."""
        self.logger.info(message)

    def debug(self, message: str) -> None:
        """Log a debug message."""
        self.logger.debug(message)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log an error message."""
        self.logger.error(message)

    def emit_event(
        self,
        event_type: EventType,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> AgentEvent:
        """Emit an event for UI streaming.

        Args:
            event_type: Type of event
            message: Optional message
            **kwargs: Additional event data

        Returns:
            The emitted AgentEvent
        """
        event = AgentEvent(
            type=event_type,
            round_num=self._round_num,
            message=message,
            **kwargs,
        )

        # Call the callback if provided
        if self.event_callback:
            self.event_callback(event)

        return event

    # Convenience methods for common prints

    def print_header(self, text: str) -> None:
        """Print a header with decorations."""
        if self.verbose:
            print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'='*60}")
            print(f"{text}")
            print(f"{'='*60}{Colors.RESET}")

    def print_subheader(self, text: str) -> None:
        """Print a subheader."""
        if self.verbose:
            print(f"\n{Colors.BOLD}{Colors.CYAN}{'-'*40}")
            print(f"{text}")
            print(f"{'-'*40}{Colors.RESET}")

    def print_status(self, icon: str, text: str, color: str = Colors.WHITE) -> None:
        """Print a status message with icon."""
        if self.verbose:
            print(f"{color}{icon} {text}{Colors.RESET}")

    def print_code(self, code: str, max_lines: int = 15) -> None:
        """Print code with syntax highlighting."""
        if not self.verbose:
            return

        lines = code.split("\n")
        if len(lines) > max_lines:
            display = "\n".join(lines[:max_lines])
            remaining = len(lines) - max_lines
            print(f"{Colors.DIM}```python{Colors.RESET}")
            print(f"{Colors.YELLOW}{display}{Colors.RESET}")
            print(f"{Colors.DIM}... ({remaining} more lines){Colors.RESET}")
            print(f"{Colors.DIM}```{Colors.RESET}")
        else:
            print(f"{Colors.DIM}```python{Colors.RESET}")
            print(f"{Colors.YELLOW}{code}{Colors.RESET}")
            print(f"{Colors.DIM}```{Colors.RESET}")

    def print_output(self, output: str, max_lines: int = 20) -> None:
        """Print execution output."""
        if not self.verbose:
            return

        lines = output.split("\n")
        if len(lines) > max_lines:
            display = "\n".join(lines[:max_lines])
            remaining = len(lines) - max_lines
            print(f"{Colors.GREEN}{display}{Colors.RESET}")
            print(f"{Colors.DIM}... ({remaining} more lines){Colors.RESET}")
        else:
            print(f"{Colors.GREEN}{output}{Colors.RESET}")

    def print_plan(self, plan_text: str) -> None:
        """Print the current plan with colored status markers."""
        if not self.verbose:
            return

        print(f"\n{Colors.BOLD}{Colors.BRIGHT_MAGENTA}Current Plan:{Colors.RESET}")
        for line in plan_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if "[x]" in line.lower():
                print(f"  {Colors.GREEN}{line}{Colors.RESET}")
            elif "[ ]" in line:
                print(f"  {Colors.YELLOW}{line}{Colors.RESET}")
            else:
                print(f"  {Colors.WHITE}{line}{Colors.RESET}")

    def print_error(self, error: str) -> None:
        """Print an error message."""
        if self.verbose:
            print(f"{Colors.BRIGHT_RED}Error:{Colors.RESET}")
            print(f"{Colors.RED}{error}{Colors.RESET}")
