"""ASCII art banner for DSAgent CLI."""

from rich.console import Console
from rich.text import Text

# ASCII art logo for DSAgent
# Note: Each line must have consistent alignment - the letters form "DSAgent"
BANNER = """\
    ____  _____  ___                    __
   / __ \\/ ___/ /   | ____ ____  ____  / /_
  / / / /\\__ \\ / /| |/ __ `/ _ \\/ __ \\/ __/
 / /_/ /___/ // ___ / /_/ /  __/ / / / /_
/_____//____//_/  |_\\__, /\\___/_/ /_/\\__/
                   /____/"""

BANNER_MINIMAL = """\
 ___  ___   _                  _
|   \\/ __| /_\\  __ _ ___ _ __ | |_
| |) \\__ \\/ _ \\/ _` / -_) '  \\|  _|
|___/|___/_/ \\_\\__, \\___|_|_|_|\\__|
               |___/"""

BANNER_BLOCKS = """\
██████╗ ███████╗ █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔══██╗██╔════╝██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
██║  ██║███████╗███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║
██║  ██║╚════██║██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║
██████╔╝███████║██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║
╚═════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝"""

TAGLINE = "AI-Powered Data Science Agent"


def print_banner(console: Console, style: str = "default") -> None:
    """Print the DSAgent banner.

    Args:
        console: Rich console instance
        style: Banner style - "default", "minimal", or "blocks"
    """
    if style == "minimal":
        banner_text = BANNER_MINIMAL
    elif style == "blocks":
        banner_text = BANNER_BLOCKS
    else:
        banner_text = BANNER

    # Create gradient colors for the banner
    lines = banner_text.split('\n')

    # Color gradient: cyan -> blue -> magenta
    colors = [
        "bright_cyan",
        "cyan",
        "dodger_blue2",
        "blue",
        "medium_purple1",
        "magenta",
    ]

    console.print()
    for i, line in enumerate(lines):
        color = colors[min(i, len(colors) - 1)]
        console.print(f"[{color}]{line}[/{color}]")

    # Tagline
    console.print()
    console.print(f"[dim italic]  {TAGLINE}[/dim italic]")
    console.print()


def print_welcome(console: Console, model: str = "", session_id: str = "") -> None:
    """Print welcome message with banner.

    Args:
        console: Rich console instance
        model: Current model name
        session_id: Current session ID
    """
    print_banner(console)

    # Session info
    if model:
        console.print(f"  [dim]Model:[/dim] [cyan]{model}[/cyan]")
    if session_id:
        console.print(f"  [dim]Session:[/dim] [cyan]{session_id}[/cyan]")

    console.print()
    console.print("  [dim]Type your message or /help for commands[/dim]")
    console.print("  [dim]Press Ctrl+C to exit[/dim]")
    console.print()


if __name__ == "__main__":
    # Test the banners
    console = Console()

    console.print("\n[bold]Default style:[/bold]")
    print_banner(console, "default")

    console.print("\n[bold]Minimal style:[/bold]")
    print_banner(console, "minimal")

    console.print("\n[bold]Blocks style:[/bold]")
    print_banner(console, "blocks")

    console.print("\n[bold]Welcome message:[/bold]")
    print_welcome(console, model="gpt-4o", session_id="abc123")
