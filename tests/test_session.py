"""Tests for session management module."""

import pytest
from datetime import datetime
from pathlib import Path

from dsagent.session.models import (
    ConversationMessage,
    MessageRole,
    ConversationHistory,
    KernelSnapshot,
    Session,
    SessionStatus,
)
from dsagent.session.store import SessionStore, JSONSessionStore, SQLiteSessionStore
from dsagent.session.manager import SessionManager


class TestConversationMessage:
    """Tests for ConversationMessage model."""

    def test_create_user_message(self):
        """Test creating a user message."""
        msg = ConversationMessage.user("Hello, world!")

        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, world!"
        assert msg.id is not None
        assert msg.timestamp is not None

    def test_create_assistant_message(self):
        """Test creating an assistant message."""
        msg = ConversationMessage.assistant("I can help with that.")

        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "I can help with that."

    def test_create_system_message(self):
        """Test creating a system message."""
        msg = ConversationMessage.system("You are a helpful assistant.")

        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "You are a helpful assistant."

    def test_create_execution_message(self):
        """Test creating an execution result message."""
        msg = ConversationMessage.execution(
            code="print('hello')",
            output="hello",
            success=True,
            execution_time=0.5
        )

        assert msg.role == MessageRole.EXECUTION
        assert "succeeded" in msg.content
        assert msg.metadata["code"] == "print('hello')"
        assert msg.metadata["output"] == "hello"
        assert msg.metadata["success"] is True
        assert msg.metadata["execution_time"] == 0.5

    def test_execution_message_failed(self):
        """Test creating a failed execution message."""
        msg = ConversationMessage.execution(
            code="1/0",
            output="ZeroDivisionError: division by zero",
            success=False
        )

        assert "failed" in msg.content
        assert msg.metadata["success"] is False

    def test_to_llm_message(self):
        """Test converting message to LLM format."""
        msg = ConversationMessage.user("Test content")
        llm_msg = msg.to_llm_message()

        assert llm_msg == {"role": "user", "content": "Test content"}

    def test_execution_to_llm_maps_to_user(self):
        """Test that execution role maps to user for LLM."""
        msg = ConversationMessage.execution("code", "output", True)
        llm_msg = msg.to_llm_message()

        assert llm_msg["role"] == "user"

    def test_message_with_metadata(self):
        """Test message with custom metadata."""
        msg = ConversationMessage.user(
            "Analyze this",
            metadata={"intent": "analysis", "priority": "high"}
        )

        assert msg.metadata["intent"] == "analysis"
        assert msg.metadata["priority"] == "high"

    def test_message_threading(self):
        """Test message parent-child relationship."""
        parent = ConversationMessage.user("Original question")
        child = ConversationMessage.assistant(
            "Follow-up response",
            parent_id=parent.id
        )

        assert child.parent_id == parent.id


class TestConversationHistory:
    """Tests for ConversationHistory model."""

    def test_add_message(self):
        """Test adding messages to history."""
        history = ConversationHistory()
        msg = ConversationMessage.user("Test")

        history.add(msg)

        assert len(history) == 1
        assert history.messages[0] == msg

    def test_add_user_message(self):
        """Test add_user convenience method."""
        history = ConversationHistory()
        msg = history.add_user("Hello")

        assert len(history) == 1
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"

    def test_add_assistant_message(self):
        """Test add_assistant convenience method."""
        history = ConversationHistory()
        msg = history.add_assistant("Response")

        assert len(history) == 1
        assert msg.role == MessageRole.ASSISTANT

    def test_add_execution(self):
        """Test add_execution convenience method."""
        history = ConversationHistory()
        msg = history.add_execution("code", "output", True)

        assert len(history) == 1
        assert msg.role == MessageRole.EXECUTION

    def test_get_recent(self):
        """Test getting recent messages."""
        history = ConversationHistory()
        for i in range(10):
            history.add_user(f"Message {i}")

        recent = history.get_recent(3)

        assert len(recent) == 3
        assert recent[0].content == "Message 7"
        assert recent[2].content == "Message 9"

    def test_get_by_role(self):
        """Test filtering messages by role."""
        history = ConversationHistory()
        history.add_user("User 1")
        history.add_assistant("Assistant 1")
        history.add_user("User 2")
        history.add_assistant("Assistant 2")

        user_msgs = history.get_by_role(MessageRole.USER)

        assert len(user_msgs) == 2
        assert all(m.role == MessageRole.USER for m in user_msgs)

    def test_to_llm_messages(self):
        """Test converting history to LLM format."""
        history = ConversationHistory()
        history.add(ConversationMessage.system("System prompt"))
        history.add_user("Question")
        history.add_assistant("Answer")

        llm_msgs = history.to_llm_messages()

        assert len(llm_msgs) == 3
        assert llm_msgs[0]["role"] == "system"
        assert llm_msgs[1]["role"] == "user"
        assert llm_msgs[2]["role"] == "assistant"

    def test_to_llm_messages_exclude_system(self):
        """Test excluding system messages from LLM output."""
        history = ConversationHistory()
        history.add(ConversationMessage.system("System prompt"))
        history.add_user("Question")

        llm_msgs = history.to_llm_messages(include_system=False)

        assert len(llm_msgs) == 1
        assert llm_msgs[0]["role"] == "user"

    def test_to_llm_messages_with_max_chars(self):
        """Test truncating LLM messages by character limit."""
        history = ConversationHistory()
        history.add_user("A" * 100)
        history.add_assistant("B" * 100)
        history.add_user("C" * 100)

        llm_msgs = history.to_llm_messages(max_chars=150)

        # Should only include most recent messages that fit
        assert len(llm_msgs) < 3

    def test_truncation_on_overflow(self):
        """Test automatic truncation when max_messages exceeded."""
        history = ConversationHistory(max_messages=5)

        for i in range(10):
            history.add_user(f"Message {i}")

        # Should have truncated to max_messages
        assert len(history) <= 5
        assert history.truncated_count > 0

    def test_clear_history(self):
        """Test clearing conversation history."""
        history = ConversationHistory()
        history.add(ConversationMessage.system("System"))
        history.add_user("User message")

        history.clear(keep_system=True)

        assert len(history) == 1
        assert history.messages[0].role == MessageRole.SYSTEM

    def test_clear_history_all(self):
        """Test clearing all history including system."""
        history = ConversationHistory()
        history.add(ConversationMessage.system("System"))
        history.add_user("User message")

        history.clear(keep_system=False)

        assert len(history) == 0

    def test_iteration(self):
        """Test iterating over history."""
        history = ConversationHistory()
        history.add_user("One")
        history.add_user("Two")

        messages = list(history)

        assert len(messages) == 2


class TestKernelSnapshot:
    """Tests for KernelSnapshot model."""

    def test_create_empty_snapshot(self):
        """Test creating an empty kernel snapshot."""
        snapshot = KernelSnapshot()

        assert snapshot.id is not None
        assert snapshot.timestamp is not None
        assert snapshot.variables == {}
        assert snapshot.dataframes == {}

    def test_snapshot_with_variables(self):
        """Test snapshot with variables."""
        snapshot = KernelSnapshot(
            variables={"x": "int", "name": "str", "data": "list"}
        )

        assert snapshot.variables["x"] == "int"
        assert len(snapshot.variables) == 3

    def test_snapshot_with_dataframes(self):
        """Test snapshot with DataFrame information."""
        snapshot = KernelSnapshot(
            variables={"df": "DataFrame"},
            dataframes={
                "df": {
                    "shape": [100, 5],
                    "columns": ["id", "name", "value", "date", "status"],
                    "dtypes": {"id": "int64", "name": "object"}
                }
            }
        )

        assert snapshot.dataframes["df"]["shape"] == [100, 5]
        assert "id" in snapshot.dataframes["df"]["columns"]

    def test_get_context_summary_empty(self):
        """Test context summary for empty kernel."""
        snapshot = KernelSnapshot()
        summary = snapshot.get_context_summary()

        assert "empty" in summary.lower()

    def test_get_context_summary_with_data(self):
        """Test context summary with variables."""
        snapshot = KernelSnapshot(
            variables={"x": "int", "df": "DataFrame"},
            dataframes={
                "df": {
                    "shape": [100, 3],
                    "columns": ["a", "b", "c"]
                }
            },
            imports=["pandas", "numpy", "sklearn"]
        )

        summary = snapshot.get_context_summary()

        assert "x: int" in summary
        assert "DataFrame" in summary
        assert "100 rows" in summary
        assert "pandas" in summary


class TestSession:
    """Tests for Session model."""

    def test_create_new_session(self):
        """Test creating a new session."""
        session = Session.new(name="Test Session")

        assert session.id is not None
        assert session.name == "Test Session"
        assert session.status == SessionStatus.ACTIVE
        assert session.created_at is not None

    def test_session_touch_updates_timestamp(self):
        """Test that touch updates the updated_at timestamp."""
        session = Session.new()
        original_time = session.updated_at

        import time
        time.sleep(0.01)
        session.touch()

        assert session.updated_at > original_time

    def test_set_workspace(self, tmp_path):
        """Test setting workspace paths."""
        session = Session.new()
        session.set_workspace(tmp_path / "workspace")

        assert session.workspace_path == str(tmp_path / "workspace")
        assert session.data_path == str(tmp_path / "workspace" / "data")
        assert session.artifacts_path == str(tmp_path / "workspace" / "artifacts")
        assert session.notebooks_path == str(tmp_path / "workspace" / "notebooks")

    def test_add_message(self):
        """Test adding messages to session."""
        session = Session.new()
        msg = ConversationMessage.user("Test message")

        session.add_message(msg)

        assert len(session.history) == 1

    def test_get_context_for_llm(self):
        """Test getting LLM context from session."""
        session = Session.new()
        session.history.add(ConversationMessage.system("System"))
        session.history.add_user("Question")

        context = session.get_context_for_llm()

        assert len(context) == 2
        assert context[0]["role"] == "system"

    def test_to_summary(self):
        """Test session summary generation."""
        session = Session.new(name="Analysis Session")
        session.history.add_user("Message 1")
        session.history.add_assistant("Response 1")

        summary = session.to_summary()

        assert summary["name"] == "Analysis Session"
        assert summary["status"] == "active"
        assert summary["message_count"] == 2


class TestJSONSessionStore:
    """Tests for JSON file-based session storage."""

    def test_save_and_load(self, tmp_path):
        """Test saving and loading a session."""
        store = JSONSessionStore(tmp_path / "sessions")
        session = Session.new(name="Test Session")
        session.history.add_user("Test message")

        store.save(session)
        loaded = store.load(session.id)

        assert loaded is not None
        assert loaded.id == session.id
        assert loaded.name == session.name
        assert len(loaded.history) == 1

    def test_load_nonexistent(self, tmp_path):
        """Test loading a non-existent session returns None."""
        store = JSONSessionStore(tmp_path / "sessions")

        loaded = store.load("nonexistent-id")

        assert loaded is None

    def test_delete(self, tmp_path):
        """Test deleting a session."""
        store = JSONSessionStore(tmp_path / "sessions")
        session = Session.new()
        store.save(session)

        result = store.delete(session.id)

        assert result is True
        assert store.load(session.id) is None

    def test_delete_nonexistent(self, tmp_path):
        """Test deleting a non-existent session."""
        store = JSONSessionStore(tmp_path / "sessions")

        result = store.delete("nonexistent-id")

        assert result is False

    def test_exists(self, tmp_path):
        """Test checking session existence."""
        store = JSONSessionStore(tmp_path / "sessions")
        session = Session.new()
        store.save(session)

        assert store.exists(session.id) is True
        assert store.exists("nonexistent") is False

    def test_list_sessions(self, tmp_path):
        """Test listing sessions."""
        store = JSONSessionStore(tmp_path / "sessions")

        # Create multiple sessions
        for i in range(3):
            session = Session.new(name=f"Session {i}")
            store.save(session)

        sessions = store.list_sessions()

        assert len(sessions) == 3

    def test_list_sessions_with_status_filter(self, tmp_path):
        """Test listing sessions filtered by status."""
        store = JSONSessionStore(tmp_path / "sessions")

        active = Session.new(name="Active")
        active.status = SessionStatus.ACTIVE
        store.save(active)

        archived = Session.new(name="Archived")
        archived.status = SessionStatus.ARCHIVED
        store.save(archived)

        active_sessions = store.list_sessions(status=SessionStatus.ACTIVE)

        assert len(active_sessions) == 1
        assert active_sessions[0]["name"] == "Active"


class TestSQLiteSessionStore:
    """Tests for SQLite-based session storage."""

    def test_save_and_load(self, tmp_path):
        """Test saving and loading a session."""
        store = SQLiteSessionStore(tmp_path / "sessions.db")
        session = Session.new(name="Test Session")
        session.history.add_user("Test message")

        store.save(session)
        loaded = store.load(session.id)

        assert loaded is not None
        assert loaded.id == session.id
        assert loaded.name == session.name
        assert len(loaded.history) == 1

    def test_load_nonexistent(self, tmp_path):
        """Test loading a non-existent session returns None."""
        store = SQLiteSessionStore(tmp_path / "sessions.db")

        loaded = store.load("nonexistent-id")

        assert loaded is None

    def test_delete(self, tmp_path):
        """Test deleting a session."""
        store = SQLiteSessionStore(tmp_path / "sessions.db")
        session = Session.new()
        store.save(session)

        result = store.delete(session.id)

        assert result is True
        assert store.load(session.id) is None

    def test_list_sessions_ordered_by_updated(self, tmp_path):
        """Test that sessions are listed by updated_at descending."""
        store = SQLiteSessionStore(tmp_path / "sessions.db")

        import time
        for i in range(3):
            session = Session.new(name=f"Session {i}")
            store.save(session)
            time.sleep(0.01)

        sessions = store.list_sessions()

        # Most recently updated should be first
        assert sessions[0]["name"] == "Session 2"


class TestSessionStore:
    """Tests for unified SessionStore."""

    def test_json_backend(self, tmp_path):
        """Test creating store with JSON backend."""
        store = SessionStore(tmp_path, backend="json")
        session = Session.new()

        store.save(session)
        loaded = store.load(session.id)

        assert loaded is not None
        assert loaded.id == session.id

    def test_sqlite_backend(self, tmp_path):
        """Test creating store with SQLite backend."""
        store = SessionStore(tmp_path, backend="sqlite")
        session = Session.new()

        store.save(session)
        loaded = store.load(session.id)

        assert loaded is not None
        assert loaded.id == session.id

    def test_invalid_backend_raises(self, tmp_path):
        """Test that invalid backend raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            SessionStore(tmp_path, backend="invalid")

        assert "Unknown backend" in str(exc_info.value)


class TestSessionManager:
    """Tests for SessionManager."""

    def test_create_session(self, tmp_path):
        """Test creating a new session."""
        manager = SessionManager(tmp_path)
        session = manager.create_session(name="My Session")

        assert session.id is not None
        assert session.name == "My Session"
        assert session.status == SessionStatus.ACTIVE
        assert Path(session.data_path).exists()

    def test_load_session(self, tmp_path):
        """Test loading an existing session."""
        manager = SessionManager(tmp_path)
        created = manager.create_session(name="Test")

        # Clear cache to force load from storage
        manager._active_sessions.clear()

        loaded = manager.load_session(created.id)

        assert loaded is not None
        assert loaded.id == created.id
        assert loaded.name == "Test"

    def test_get_or_create_existing(self, tmp_path):
        """Test get_or_create returns existing session."""
        manager = SessionManager(tmp_path)
        created = manager.create_session(name="Existing")

        session = manager.get_or_create(created.id)

        assert session.id == created.id

    def test_get_or_create_new(self, tmp_path):
        """Test get_or_create creates new session when not found."""
        manager = SessionManager(tmp_path)

        session = manager.get_or_create(name="New Session")

        assert session is not None
        assert session.name == "New Session"

    def test_delete_session(self, tmp_path):
        """Test deleting a session."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()

        result = manager.delete_session(session.id)

        assert result is True
        assert manager.load_session(session.id) is None

    def test_archive_session(self, tmp_path):
        """Test archiving a session."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()

        result = manager.archive_session(session.id)

        assert result is True
        loaded = manager.load_session(session.id)
        assert loaded.status == SessionStatus.ARCHIVED

    def test_list_sessions(self, tmp_path):
        """Test listing sessions."""
        manager = SessionManager(tmp_path)
        manager.create_session(name="Session 1")
        manager.create_session(name="Session 2")

        sessions = manager.list_sessions()

        assert len(sessions) == 2

    def test_add_message(self, tmp_path):
        """Test adding a message through manager."""
        manager = SessionManager(tmp_path, auto_save=True)
        session = manager.create_session()

        msg = manager.add_user_message(session, "Hello")

        assert len(session.history) == 1
        assert msg.content == "Hello"

    def test_add_execution_result(self, tmp_path):
        """Test adding execution result through manager."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()

        msg = manager.add_execution_result(
            session,
            code="print('hi')",
            output="hi",
            success=True
        )

        assert len(session.history) == 1
        assert msg.role == MessageRole.EXECUTION

    def test_update_kernel_snapshot(self, tmp_path):
        """Test updating kernel snapshot."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()
        snapshot = KernelSnapshot(variables={"x": "int"})

        manager.update_kernel_snapshot(session, snapshot)

        assert session.kernel_snapshot is not None
        assert session.kernel_snapshot.variables["x"] == "int"

    def test_on_change_callback(self, tmp_path):
        """Test that change callbacks are called."""
        manager = SessionManager(tmp_path)
        changes = []

        manager.on_change(lambda s: changes.append(s.id))

        session = manager.create_session()
        manager.save_session(session)

        assert session.id in changes

    def test_context_manager(self, tmp_path):
        """Test using manager as context manager."""
        with SessionManager(tmp_path) as manager:
            session = manager.create_session()
            manager.add_user_message(session, "Test")

        # Should have saved on exit
        new_manager = SessionManager(tmp_path)
        loaded = new_manager.load_session(session.id)
        assert loaded is not None
        assert len(loaded.history) == 1

    def test_session_id_format(self, tmp_path):
        """Test that session IDs have correct format."""
        manager = SessionManager(tmp_path)
        session = manager.create_session()

        # Format: YYYYMMDD_HHMMSS_XXXXXX
        parts = session.id.split("_")
        assert len(parts) == 3
        assert len(parts[0]) == 8  # YYYYMMDD
        assert len(parts[1]) == 6  # HHMMSS
        assert len(parts[2]) == 6  # short uuid
