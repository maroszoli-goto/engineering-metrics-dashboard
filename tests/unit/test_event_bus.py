"""Tests for event bus system."""

import pytest

from src.dashboard.events import EventBus, get_event_bus, reset_event_bus


class TestEventBus:
    """Tests for EventBus class."""

    @pytest.fixture
    def event_bus(self):
        """Create fresh event bus for each test."""
        return EventBus()

    def test_subscribe_and_publish(self, event_bus):
        """Test basic subscribe and publish."""
        received_events = []

        def handler(event_data):
            received_events.append(event_data)

        event_bus.subscribe("test_event", handler)
        event_bus.publish("test_event", {"data": "test"})

        assert len(received_events) == 1
        assert received_events[0] == {"data": "test"}

    def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers for same event."""
        received_1 = []
        received_2 = []

        event_bus.subscribe("test_event", lambda e: received_1.append(e))
        event_bus.subscribe("test_event", lambda e: received_2.append(e))

        event_bus.publish("test_event", "data")

        assert len(received_1) == 1
        assert len(received_2) == 1

    def test_unsubscribe(self, event_bus):
        """Test unsubscribing from events."""
        received = []

        def handler(event_data):
            received.append(event_data)

        event_bus.subscribe("test_event", handler)
        event_bus.publish("test_event", "first")
        assert len(received) == 1

        event_bus.unsubscribe("test_event", handler)
        event_bus.publish("test_event", "second")
        assert len(received) == 1  # Still 1, not 2

    def test_publish_no_subscribers(self, event_bus):
        """Test publishing with no subscribers doesn't error."""
        # Should not raise
        event_bus.publish("nonexistent_event", "data")

    def test_subscriber_error_doesnt_break_others(self, event_bus):
        """Test that error in one subscriber doesn't affect others."""
        received = []

        def bad_handler(event_data):
            raise ValueError("Handler error")

        def good_handler(event_data):
            received.append(event_data)

        event_bus.subscribe("test_event", bad_handler)
        event_bus.subscribe("test_event", good_handler)

        event_bus.publish("test_event", "data")

        # Good handler should still receive
        assert len(received) == 1

    def test_clear_subscribers_specific(self, event_bus):
        """Test clearing subscribers for specific event."""
        received = []

        event_bus.subscribe("event1", lambda e: received.append("event1"))
        event_bus.subscribe("event2", lambda e: received.append("event2"))

        event_bus.clear_subscribers("event1")

        event_bus.publish("event1", None)
        event_bus.publish("event2", None)

        # Only event2 handler should fire
        assert len(received) == 1
        assert received[0] == "event2"

    def test_clear_all_subscribers(self, event_bus):
        """Test clearing all subscribers."""
        received = []

        event_bus.subscribe("event1", lambda e: received.append("event1"))
        event_bus.subscribe("event2", lambda e: received.append("event2"))

        event_bus.clear_subscribers()  # No arg = clear all

        event_bus.publish("event1", None)
        event_bus.publish("event2", None)

        # No handlers should fire
        assert len(received) == 0

    def test_get_subscriber_count(self, event_bus):
        """Test getting subscriber count."""
        assert event_bus.get_subscriber_count("test_event") == 0

        event_bus.subscribe("test_event", lambda e: None)
        assert event_bus.get_subscriber_count("test_event") == 1

        event_bus.subscribe("test_event", lambda e: None)
        assert event_bus.get_subscriber_count("test_event") == 2

    def test_unsubscribe_nonexistent_handler(self, event_bus):
        """Test unsubscribing handler that wasn't subscribed."""
        # Should not raise
        event_bus.unsubscribe("test_event", lambda e: None)


class TestGlobalEventBus:
    """Tests for global event bus singleton."""

    def teardown_method(self):
        """Reset global event bus after each test."""
        reset_event_bus()

    def test_get_event_bus_returns_singleton(self):
        """Test that get_event_bus returns same instance."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2

    def test_reset_event_bus(self):
        """Test resetting global event bus."""
        bus1 = get_event_bus()

        reset_event_bus()

        bus2 = get_event_bus()

        assert bus1 is not bus2

    def test_global_bus_state_persists(self):
        """Test that global bus state persists across calls."""
        bus = get_event_bus()

        received = []
        bus.subscribe("test", lambda e: received.append(e))

        # Get bus again and publish
        bus2 = get_event_bus()
        bus2.publish("test", "data")

        assert len(received) == 1


class TestEventBusIntegration:
    """Integration tests for event bus."""

    def test_event_data_none(self):
        """Test publishing event with None data."""
        bus = EventBus()
        received = []

        bus.subscribe("test", lambda e: received.append(e))
        bus.publish("test", None)

        assert len(received) == 1
        assert received[0] is None

    def test_event_data_complex_object(self):
        """Test publishing event with complex data."""
        bus = EventBus()
        received = []

        bus.subscribe("test", lambda e: received.append(e))

        complex_data = {
            "nested": {
                "list": [1, 2, 3],
                "dict": {"key": "value"},
            },
            "number": 42,
        }

        bus.publish("test", complex_data)

        assert len(received) == 1
        assert received[0] == complex_data

    def test_subscriber_can_modify_state(self):
        """Test that subscribers can modify external state."""
        bus = EventBus()
        counter = {"count": 0}

        def increment_handler(event_data):
            counter["count"] += event_data

        bus.subscribe("increment", increment_handler)

        bus.publish("increment", 5)
        bus.publish("increment", 3)

        assert counter["count"] == 8
