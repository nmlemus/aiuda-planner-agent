"""Tests for conversational CLI module."""

import pytest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from rich.console import Console

from dsagent.cli.commands import (
    Command,
    CommandRegistry,
    CommandResult,
    HelpCommand,
    NewCommand,
    SessionsCommand,
    LoadCommand,
    ContextCommand,
    VarsCommand,
    HistoryCommand,
    ClearCommand,
    QuitCommand,
    StatusCommand,
    ModelCommand,
    DataCommand,
    WorkspaceCommand,
    create_default_registry,
)
from dsagent.cli.repl import CLIContext, ConversationalCLI
from dsagent.cli.renderer import CLIRenderer
from dsagent.session import Session, SessionManager, KernelSnapshot


class TestCommandRegistry:
    """Tests for CommandRegistry."""

    def test_register_command(self):
        """Test registering a command."""
        registry = CommandRegistry()
        cmd = HelpCommand()

        registry.register(cmd)

        assert registry.get("help") == cmd

    def test_get_by_alias(self):
        """Test getting command by alias."""
        registry = CommandRegistry()
        cmd = HelpCommand()
        registry.register(cmd)

        assert registry.get("h") == cmd
        assert registry.get("?") == cmd

    def test_get_nonexistent(self):
        """Test getting non-existent command."""
        registry = CommandRegistry()

        assert registry.get("nonexistent") is None

    def test_list_commands(self):
        """Test listing all commands."""
        registry = CommandRegistry()
        registry.register(HelpCommand())
        registry.register(QuitCommand())

        commands = registry.list_commands()

        assert len(commands) == 2
        assert any(c.name == "help" for c in commands)
        assert any(c.name == "quit" for c in commands)

    def test_get_completions(self):
        """Test command completions."""
        registry = CommandRegistry()
        registry.register(HelpCommand())
        registry.register(HistoryCommand())

        completions = registry.get_completions("h")

        assert "/help" in completions
        assert "/history" in completions
        assert "/hist" in completions  # alias

    def test_create_default_registry(self):
        """Test default registry has all commands."""
        registry = create_default_registry()

        # Check core commands exist
        assert registry.get("help") is not None
        assert registry.get("new") is not None
        assert registry.get("sessions") is not None
        assert registry.get("load") is not None
        assert registry.get("quit") is not None
        assert registry.get("status") is not None


class TestCommandResult:
    """Tests for CommandResult."""

    def test_default_success(self):
        """Test default result is success."""
        result = CommandResult()

        assert result.success is True
        assert result.should_exit is False
        assert result.clear_screen is False

    def test_with_message(self):
        """Test result with message."""
        result = CommandResult(message="Hello")

        assert result.message == "Hello"

    def test_failure(self):
        """Test failure result."""
        result = CommandResult(success=False, message="Error occurred")

        assert result.success is False
        assert result.message == "Error occurred"

    def test_exit_flag(self):
        """Test exit flag."""
        result = CommandResult(should_exit=True)

        assert result.should_exit is True


class TestCLIContext:
    """Tests for CLIContext."""

    def test_create_context(self, tmp_path):
        """Test creating CLI context."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()

        ctx = CLIContext(
            manager=manager,
            registry=registry,
            console=console,
            model="gpt-4o"
        )

        assert ctx.model == "gpt-4o"
        assert ctx.session is None

    def test_set_session(self, tmp_path):
        """Test setting session."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()

        ctx = CLIContext(
            manager=manager,
            registry=registry,
            console=console,
        )

        session = Session.new(name="Test")
        ctx.set_session(session)

        assert ctx.session == session
        assert ctx.has_active_session() is True

    def test_has_active_session_false(self, tmp_path):
        """Test has_active_session when no session."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()

        ctx = CLIContext(
            manager=manager,
            registry=registry,
            console=console,
        )

        assert ctx.has_active_session() is False


class TestHelpCommand:
    """Tests for HelpCommand."""

    def test_general_help(self, tmp_path):
        """Test general help output."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = HelpCommand()
        result = cmd.execute(ctx, [])

        assert result.success is True
        assert "Available commands" in result.message
        assert "/help" in result.message

    def test_specific_command_help(self, tmp_path):
        """Test help for specific command."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = HelpCommand()
        result = cmd.execute(ctx, ["new"])

        assert result.success is True
        assert "new" in result.message
        assert "session" in result.message.lower()

    def test_unknown_command_help(self, tmp_path):
        """Test help for unknown command."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = HelpCommand()
        result = cmd.execute(ctx, ["nonexistent"])

        assert result.success is False
        assert "Unknown command" in result.message


class TestNewCommand:
    """Tests for NewCommand."""

    def test_create_new_session(self, tmp_path):
        """Test creating new session."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = NewCommand()
        result = cmd.execute(ctx, [])

        assert result.success is True
        assert ctx.session is not None
        assert "New session created" in result.message

    def test_create_named_session(self, tmp_path):
        """Test creating named session."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = NewCommand()
        result = cmd.execute(ctx, ["My", "Analysis"])

        assert result.success is True
        assert ctx.session.name == "My Analysis"


class TestSessionsCommand:
    """Tests for SessionsCommand."""

    def test_list_empty(self, tmp_path):
        """Test listing sessions when none exist."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = SessionsCommand()
        result = cmd.execute(ctx, [])

        assert "No sessions found" in result.message

    def test_list_sessions(self, tmp_path):
        """Test listing sessions."""
        manager = SessionManager(tmp_path)
        manager.create_session(name="Session 1")
        manager.create_session(name="Session 2")

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = SessionsCommand()
        result = cmd.execute(ctx, [])

        assert result.success is True
        assert "Session 1" in result.message or "Session 2" in result.message


class TestLoadCommand:
    """Tests for LoadCommand."""

    def test_load_no_id(self, tmp_path):
        """Test load without session ID."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = LoadCommand()
        result = cmd.execute(ctx, [])

        assert result.success is False
        assert "Session ID required" in result.message

    def test_load_nonexistent(self, tmp_path):
        """Test loading non-existent session."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = LoadCommand()
        result = cmd.execute(ctx, ["nonexistent123"])

        assert result.success is False
        assert "No session found" in result.message

    def test_load_existing(self, tmp_path):
        """Test loading existing session."""
        manager = SessionManager(tmp_path)
        session = manager.create_session(name="Test Session")
        session_id = session.id

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = LoadCommand()
        result = cmd.execute(ctx, [session_id[:8]])

        assert result.success is True
        assert ctx.session is not None
        assert "Loaded session" in result.message


class TestContextCommand:
    """Tests for ContextCommand."""

    def test_no_session(self, tmp_path):
        """Test context with no session."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = ContextCommand()
        result = cmd.execute(ctx, [])

        assert "No active session" in result.message

    def test_no_kernel_snapshot(self, tmp_path):
        """Test context with no kernel snapshot."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)
        ctx.set_session(session)

        cmd = ContextCommand()
        result = cmd.execute(ctx, [])

        assert "not available" in result.message

    def test_with_kernel_snapshot(self, tmp_path):
        """Test context with kernel snapshot."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()
        session.kernel_snapshot = KernelSnapshot(
            variables={"x": "int", "df": "DataFrame"},
            dataframes={"df": {"shape": [100, 5], "columns": ["a", "b", "c", "d", "e"]}}
        )

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)
        ctx.set_session(session)

        cmd = ContextCommand()
        result = cmd.execute(ctx, [])

        assert result.success is True
        assert "x" in result.message or "df" in result.message


class TestVarsCommand:
    """Tests for VarsCommand."""

    def test_no_kernel_state(self, tmp_path):
        """Test vars with no kernel state."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)
        ctx.set_session(session)

        cmd = VarsCommand()
        result = cmd.execute(ctx, [])

        assert "No kernel state" in result.message

    def test_with_variables(self, tmp_path):
        """Test vars with variables."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()
        session.kernel_snapshot = KernelSnapshot(
            variables={"x": "int", "name": "str"}
        )

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)
        ctx.set_session(session)

        cmd = VarsCommand()
        result = cmd.execute(ctx, [])

        assert "x" in result.message
        assert "int" in result.message


class TestHistoryCommand:
    """Tests for HistoryCommand."""

    def test_no_session(self, tmp_path):
        """Test history with no session."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = HistoryCommand()
        result = cmd.execute(ctx, [])

        assert "No active session" in result.message

    def test_empty_history(self, tmp_path):
        """Test history when empty."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)
        ctx.set_session(session)

        cmd = HistoryCommand()
        result = cmd.execute(ctx, [])

        assert "No messages" in result.message

    def test_with_messages(self, tmp_path):
        """Test history with messages."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()
        manager.add_user_message(session, "Hello")
        manager.add_assistant_message(session, "Hi there")

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)
        ctx.set_session(session)

        cmd = HistoryCommand()
        result = cmd.execute(ctx, [])

        assert "user" in result.message
        assert "assistant" in result.message


class TestClearCommand:
    """Tests for ClearCommand."""

    def test_clear_sets_flag(self, tmp_path):
        """Test clear command sets clear_screen flag."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = ClearCommand()
        result = cmd.execute(ctx, [])

        assert result.clear_screen is True


class TestQuitCommand:
    """Tests for QuitCommand."""

    def test_quit_sets_exit(self, tmp_path):
        """Test quit command sets should_exit flag."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = QuitCommand()
        result = cmd.execute(ctx, [])

        assert result.should_exit is True
        assert "Goodbye" in result.message

    def test_quit_saves_session(self, tmp_path):
        """Test quit saves active session."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()
        manager.add_user_message(session, "Test message")

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)
        ctx.set_session(session)

        cmd = QuitCommand()
        result = cmd.execute(ctx, [])

        # Verify session was saved
        loaded = manager.load_session(session.id)
        assert len(loaded.history) == 1


class TestStatusCommand:
    """Tests for StatusCommand."""

    def test_no_session(self, tmp_path):
        """Test status with no session."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)

        cmd = StatusCommand()
        result = cmd.execute(ctx, [])

        assert "No active session" in result.message

    def test_with_session(self, tmp_path):
        """Test status with active session."""
        manager = SessionManager(tmp_path)
        session = manager.create_session(name="Analysis")

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)
        ctx.set_session(session)
        ctx.model = "gpt-4o"

        cmd = StatusCommand()
        result = cmd.execute(ctx, [])

        assert "Analysis" in result.message
        assert "gpt-4o" in result.message


class TestModelCommand:
    """Tests for ModelCommand."""

    def test_show_current_model(self, tmp_path):
        """Test showing current model."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)
        ctx.model = "claude-3-opus"

        cmd = ModelCommand()
        result = cmd.execute(ctx, [])

        assert "claude-3-opus" in result.message

    def test_change_model(self, tmp_path):
        """Test changing model."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console)
        ctx.model = "gpt-4o"

        cmd = ModelCommand()
        result = cmd.execute(ctx, ["gpt-4o-mini"])

        assert ctx.model == "gpt-4o-mini"
        assert "changed" in result.message


class TestCLIRenderer:
    """Tests for CLIRenderer."""

    def test_render_code(self, tmp_path):
        """Test rendering code."""
        console = Console(file=StringIO(), force_terminal=True)
        renderer = CLIRenderer(console)

        renderer.render_code("print('hello')", language="python")

        output = console.file.getvalue()
        assert "print" in output

    def test_render_output_success(self, tmp_path):
        """Test rendering successful output."""
        console = Console(file=StringIO(), force_terminal=True)
        renderer = CLIRenderer(console)

        renderer.render_output("Result: 42", success=True)

        output = console.file.getvalue()
        assert "42" in output

    def test_render_output_failure(self, tmp_path):
        """Test rendering failed output."""
        console = Console(file=StringIO(), force_terminal=True)
        renderer = CLIRenderer(console)

        renderer.render_output("Error: Division by zero", success=False)

        output = console.file.getvalue()
        assert "Division" in output

    def test_render_variables(self, tmp_path):
        """Test rendering variables."""
        console = Console(file=StringIO(), force_terminal=True)
        renderer = CLIRenderer(console)

        renderer.render_variables(
            {"x": "int", "df": "DataFrame"},
            dataframes={"df": {"shape": [100, 5], "columns": ["a", "b", "c"]}}
        )

        output = console.file.getvalue()
        assert "x" in output or "df" in output

    def test_render_error(self, tmp_path):
        """Test rendering error message."""
        console = Console(file=StringIO(), force_terminal=True)
        renderer = CLIRenderer(console)

        renderer.render_error("Something went wrong")

        output = console.file.getvalue()
        assert "wrong" in output

    def test_render_success(self, tmp_path):
        """Test rendering success message."""
        console = Console(file=StringIO(), force_terminal=True)
        renderer = CLIRenderer(console)

        renderer.render_success("Operation completed")

        output = console.file.getvalue()
        assert "completed" in output


class TestConversationalCLI:
    """Tests for ConversationalCLI."""

    def test_init(self, tmp_path):
        """Test CLI initialization."""
        cli = ConversationalCLI(workspace=tmp_path)

        assert cli.workspace == tmp_path
        assert cli.ctx is not None
        assert cli.registry is not None

    def test_handle_command(self, tmp_path):
        """Test handling slash command."""
        cli = ConversationalCLI(workspace=tmp_path)

        # Handle help command
        result = cli._handle_command("/help")

        assert result is True  # Should continue running

    def test_handle_quit_command(self, tmp_path):
        """Test handling quit command."""
        cli = ConversationalCLI(workspace=tmp_path)

        result = cli._handle_command("/quit")

        assert result is False  # Should exit

    def test_handle_unknown_command(self, tmp_path, capsys):
        """Test handling unknown command."""
        cli = ConversationalCLI(workspace=tmp_path)

        result = cli._handle_command("/unknowncommand")

        assert result is True  # Should continue

    def test_get_prompt_no_session(self, tmp_path):
        """Test prompt without session."""
        cli = ConversationalCLI(workspace=tmp_path)

        prompt = cli._get_prompt()

        assert "no session" in prompt

    def test_get_prompt_with_session(self, tmp_path):
        """Test prompt with session."""
        cli = ConversationalCLI(workspace=tmp_path)
        session = cli.manager.create_session()
        cli.ctx.set_session(session)

        prompt = cli._get_prompt()

        assert "You>" in prompt


class TestDataCommand:
    """Tests for DataCommand."""

    def test_list_empty_data_dir_no_session(self, tmp_path):
        """Test listing files when data directory is empty (no session)."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console, workspace=tmp_path)

        cmd = DataCommand()
        result = cmd.execute(ctx, [])

        assert "No files in data/" in result.message

    def test_copy_file_to_session_data(self, tmp_path):
        """Test copying a file to session's data directory."""
        # Create a source file
        source_file = tmp_path / "source.csv"
        source_file.write_text("a,b,c\n1,2,3\n")

        manager = SessionManager(tmp_path)
        session = manager.create_session(name="Test")
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console, workspace=tmp_path)
        ctx.set_session(session)

        cmd = DataCommand()
        result = cmd.execute(ctx, [str(source_file)])

        assert result.success is True
        assert "Copied: source.csv" in result.message
        # File should be in session's data directory, not workspace/data
        assert Path(session.data_path, "source.csv").exists()
        assert not (tmp_path / "data" / "source.csv").exists()

    def test_copy_directory_to_session_data(self, tmp_path):
        """Test copying a directory to session's data directory."""
        # Create a source directory with files
        source_dir = tmp_path / "source_data"
        source_dir.mkdir()
        (source_dir / "file1.csv").write_text("a,b\n1,2\n")
        (source_dir / "file2.csv").write_text("x,y\n3,4\n")

        manager = SessionManager(tmp_path)
        session = manager.create_session(name="Test")
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console, workspace=tmp_path)
        ctx.set_session(session)

        cmd = DataCommand()
        result = cmd.execute(ctx, [str(source_dir)])

        assert result.success is True
        assert "Copied 2 files" in result.message
        # Files should be in session's data directory
        assert Path(session.data_path, "file1.csv").exists()
        assert Path(session.data_path, "file2.csv").exists()

    def test_copy_nonexistent_file(self, tmp_path):
        """Test copying a file that doesn't exist."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console, workspace=tmp_path)

        cmd = DataCommand()
        result = cmd.execute(ctx, ["/nonexistent/file.csv"])

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_list_session_data_files(self, tmp_path):
        """Test listing files in session's data directory."""
        manager = SessionManager(tmp_path)
        session = manager.create_session(name="Test")

        # Create files in session's data directory
        data_dir = Path(session.data_path)
        (data_dir / "file1.csv").write_text("data")
        (data_dir / "file2.json").write_text("{}")

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console, workspace=tmp_path)
        ctx.set_session(session)

        cmd = DataCommand()
        result = cmd.execute(ctx, [])

        assert result.success is True
        assert "file1.csv" in result.message
        assert "file2.json" in result.message


class TestWorkspaceCommand:
    """Tests for WorkspaceCommand."""

    def test_workspace_no_session(self, tmp_path):
        """Test workspace info when no session (uses ctx.workspace)."""
        manager = SessionManager(tmp_path)
        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console, workspace=tmp_path)

        cmd = WorkspaceCommand()
        result = cmd.execute(ctx, [])

        assert result.success is True
        assert str(tmp_path) in result.message
        assert "not created" in result.message

    def test_workspace_with_session(self, tmp_path):
        """Test workspace info with active session."""
        manager = SessionManager(tmp_path)
        session = manager.create_session(name="Test")

        # Create files in session's data directory
        data_dir = Path(session.data_path)
        (data_dir / "file1.csv").write_text("data")
        (data_dir / "file2.csv").write_text("more data")

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console, workspace=tmp_path)
        ctx.set_session(session)

        cmd = WorkspaceCommand()
        result = cmd.execute(ctx, [])

        assert result.success is True
        # Should show session's workspace path (runs/{session_id})
        assert session.workspace_path in result.message
        assert "data/: 2 file(s)" in result.message

    def test_workspace_with_session_artifacts(self, tmp_path):
        """Test workspace info with session artifact files."""
        manager = SessionManager(tmp_path)
        session = manager.create_session(name="Test")

        # Create artifacts in session's artifacts directory
        artifacts_dir = Path(session.artifacts_path)
        (artifacts_dir / "plot.png").write_text("fake image")
        (artifacts_dir / "model.pkl").write_text("fake model")
        (artifacts_dir / "report.html").write_text("<html>")

        registry = create_default_registry()
        console = Console()
        ctx = CLIContext(manager=manager, registry=registry, console=console, workspace=tmp_path)
        ctx.set_session(session)

        cmd = WorkspaceCommand()
        result = cmd.execute(ctx, [])

        assert result.success is True
        assert "artifacts/: 3 file(s)" in result.message
