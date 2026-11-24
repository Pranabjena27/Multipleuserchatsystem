"""
Socket State and In-Memory Presence Management Module
=====================================================
Thread-safe tracking of connected sockets, online users, active rooms,
and transient typing states.
"""

from collections import defaultdict
import threading
from typing import Set, Dict


class SocketStateManager:
    """
    Manages in-memory presence and room bindings for connected WebSocket clients.
    Thread-safe using Python's threading.RLock.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Mapping: user_id -> set of active socket_ids (supports multiple tabs/devices)
        self._user_sockets: Dict[int, Set[str]] = defaultdict(set)
        # Mapping: socket_id -> user_id
        self._socket_to_user: Dict[str, int] = {}
        # Mapping: conversation_id -> set of active user_ids currently in room
        self._room_users: Dict[int, Set[int]] = defaultdict(set)
        # Mapping: conversation_id -> dict of {user_id: timestamp} who are currently typing
        self._typing_users: Dict[int, Dict[int, float]] = defaultdict(dict)

    def register_socket(self, user_id: int, socket_id: str) -> bool:
        """
        Register a newly connected socket ID for a user.
        Returns True if this is the user's first active connection (user just came online).
        """
        with self._lock:
            self._socket_to_user[socket_id] = user_id
            user_set = self._user_sockets[user_id]
            first_connection = len(user_set) == 0
            user_set.add(socket_id)
            return first_connection

    def unregister_socket(self, socket_id: str) -> tuple[int | None, bool]:
        """
        Unregister a disconnected socket ID.
        Returns: (user_id, has_gone_offline_bool)
        """
        with self._lock:
            user_id = self._socket_to_user.pop(socket_id, None)
            if user_id is None:
                return None, False

            user_set = self._user_sockets[user_id]
            user_set.discard(socket_id)
            has_gone_offline = len(user_set) == 0
            if has_gone_offline:
                self._user_sockets.pop(user_id, None)

            # Cleanup typing state across all rooms
            for room_id in list(self._typing_users.keys()):
                self._typing_users[room_id].pop(user_id, None)

            return user_id, has_gone_offline

    def is_user_online(self, user_id: int) -> bool:
        """Check if user has at least one active socket connected."""
        with self._lock:
            return len(self._user_sockets.get(user_id, set())) > 0

    def get_user_sockets(self, user_id: int) -> list[str]:
        """Get all socket IDs for a given user."""
        with self._lock:
            return list(self._user_sockets.get(user_id, set()))

    def get_online_users(self) -> list[int]:
        """Return list of all currently connected user IDs."""
        with self._lock:
            return list(self._user_sockets.keys())

    def user_joined_room(self, user_id: int, conversation_id: int) -> None:
        """Track user presence inside an active conversation room."""
        with self._lock:
            self._room_users[conversation_id].add(user_id)

    def user_left_room(self, user_id: int, conversation_id: int) -> None:
        """Track user exit from an active conversation room."""
        with self._lock:
            self._room_users[conversation_id].discard(user_id)
            self._typing_users[conversation_id].pop(user_id, None)

    def set_typing(self, user_id: int, conversation_id: int, is_typing: bool, timestamp: float) -> None:
        """Update typing indicator state."""
        with self._lock:
            if is_typing:
                self._typing_users[conversation_id][user_id] = timestamp
            else:
                self._typing_users[conversation_id].pop(user_id, None)

    def get_typing_users(self, conversation_id: int) -> list[int]:
        """Retrieve list of user IDs currently typing in a conversation."""
        with self._lock:
            return list(self._typing_users.get(conversation_id, {}).keys())


# Singleton socket state manager instance
socket_state = SocketStateManager()

