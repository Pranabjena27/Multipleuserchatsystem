"""
SocketIO Real-Time Communications Test Suite
============================================
Validates in-memory presence tracking and WebSocket events.
"""

from app.sockets.state import SocketStateManager


def test_socket_state_manager_presence():
    """Test thread-safe presence state transitions for multi-tab connections."""
    manager = SocketStateManager()

    user_id = 42
    socket_1 = "sid_abc_1"
    socket_2 = "sid_abc_2"

    # Tab 1 connects -> user becomes online
    first_conn = manager.register_socket(user_id, socket_1)
    assert first_conn is True
    assert manager.is_user_online(user_id) is True

    # Tab 2 connects -> user still online
    second_conn = manager.register_socket(user_id, socket_2)
    assert second_conn is False
    assert manager.is_user_online(user_id) is True

    # Tab 1 disconnects -> user remains online because Tab 2 is active
    _, gone_offline = manager.unregister_socket(socket_1)
    assert gone_offline is False
    assert manager.is_user_online(user_id) is True

    # Tab 2 disconnects -> user goes offline
    _, gone_offline_2 = manager.unregister_socket(socket_2)
    assert gone_offline_2 is True
    assert manager.is_user_online(user_id) is False


def test_socket_state_manager_typing():
    """Test typing indicator tracking and cleanup."""
    manager = SocketStateManager()

    conv_id = 99
    user_id = 10

    manager.set_typing(user_id, conv_id, True, 1700000000.0)
    assert user_id in manager.get_typing_users(conv_id)

    manager.set_typing(user_id, conv_id, False, 0.0)
    assert user_id not in manager.get_typing_users(conv_id)
