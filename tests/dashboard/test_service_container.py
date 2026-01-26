"""Tests for ServiceContainer dependency injection

Tests cover service registration, resolution, lifecycle management,
and error handling scenarios.
"""

import pytest

from src.dashboard.services.service_container import ServiceContainer


class TestServiceRegistration:
    """Test service registration and basic operations"""

    def test_register_singleton_service(self):
        """Test registering a singleton service"""
        container = ServiceContainer()
        container.register("test_service", lambda c: "test_value", singleton=True)

        assert container.has("test_service")

    def test_register_transient_service(self):
        """Test registering a transient service"""
        container = ServiceContainer()
        container.register("test_service", lambda c: "test_value", singleton=False)

        assert container.has("test_service")

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate service raises ValueError"""
        container = ServiceContainer()
        container.register("test_service", lambda c: "value1")

        with pytest.raises(ValueError, match="already registered"):
            container.register("test_service", lambda c: "value2")

    def test_has_returns_false_for_unregistered(self):
        """Test has() returns False for unregistered services"""
        container = ServiceContainer()
        assert not container.has("nonexistent")


class TestServiceResolution:
    """Test service instance resolution and caching"""

    def test_get_singleton_returns_same_instance(self):
        """Test singleton services return same instance"""
        container = ServiceContainer()
        call_count = [0]

        def factory(c):
            call_count[0] += 1
            return {"count": call_count[0]}

        container.register("singleton", factory, singleton=True)

        instance1 = container.get("singleton")
        instance2 = container.get("singleton")

        assert instance1 is instance2  # Same object
        assert call_count[0] == 1  # Factory called once

    def test_get_transient_returns_new_instance(self):
        """Test transient services return new instance each time"""
        container = ServiceContainer()
        call_count = [0]

        def factory(c):
            call_count[0] += 1
            return {"count": call_count[0]}

        container.register("transient", factory, singleton=False)

        instance1 = container.get("transient")
        instance2 = container.get("transient")

        assert instance1 is not instance2  # Different objects
        assert instance1["count"] == 1
        assert instance2["count"] == 2
        assert call_count[0] == 2  # Factory called twice

    def test_get_unregistered_raises_key_error(self):
        """Test getting unregistered service raises KeyError with helpful message"""
        container = ServiceContainer()
        container.register("service_a", lambda c: "a")
        container.register("service_b", lambda c: "b")

        with pytest.raises(KeyError) as exc_info:
            container.get("nonexistent")

        error_msg = str(exc_info.value)
        assert "nonexistent" in error_msg
        assert "service_a" in error_msg  # Shows available services
        assert "service_b" in error_msg


class TestDependencyInjection:
    """Test automatic dependency resolution"""

    def test_resolve_simple_dependency(self):
        """Test service depending on another service"""
        container = ServiceContainer()

        # Register config service
        container.register("config", lambda c: {"name": "test"})

        # Register service that depends on config
        container.register("dependent", lambda c: {"config": c.get("config"), "extra": "data"})

        result = container.get("dependent")
        assert result["config"] == {"name": "test"}
        assert result["extra"] == "data"

    def test_resolve_chain_of_dependencies(self):
        """Test service with transitive dependencies"""
        container = ServiceContainer()

        # A depends on nothing
        container.register("service_a", lambda c: {"name": "A"})

        # B depends on A
        container.register("service_b", lambda c: {"name": "B", "a": c.get("service_a")})

        # C depends on B (which depends on A)
        container.register("service_c", lambda c: {"name": "C", "b": c.get("service_b")})

        result = container.get("service_c")
        assert result["name"] == "C"
        assert result["b"]["name"] == "B"
        assert result["b"]["a"]["name"] == "A"

    def test_circular_dependency_raises_error(self):
        """Test circular dependencies are detected and raise RuntimeError"""
        container = ServiceContainer()

        # A depends on B, B depends on A (circular)
        container.register("service_a", lambda c: {"b": c.get("service_b")})
        container.register("service_b", lambda c: {"a": c.get("service_a")})

        with pytest.raises(RuntimeError, match="Circular dependency detected"):
            container.get("service_a")

    def test_self_reference_raises_error(self):
        """Test service referencing itself raises error"""
        container = ServiceContainer()
        container.register("self_ref", lambda c: {"self": c.get("self_ref")})

        with pytest.raises(RuntimeError, match="Circular dependency"):
            container.get("self_ref")


class TestContainerMethods:
    """Test container utility methods"""

    def test_list_services_empty(self):
        """Test list_services on empty container"""
        container = ServiceContainer()
        assert container.list_services() == {}

    def test_list_services_shows_registration_info(self):
        """Test list_services shows singleton and instantiation status"""
        container = ServiceContainer()

        container.register("singleton", lambda c: "value", singleton=True)
        container.register("transient", lambda c: "value", singleton=False)

        # Before instantiation
        services = container.list_services()
        assert services["singleton"]["singleton"] is True
        assert services["singleton"]["instantiated"] is False
        assert services["transient"]["singleton"] is False
        assert services["transient"]["instantiated"] is False

        # After instantiation
        container.get("singleton")
        services = container.list_services()
        assert services["singleton"]["instantiated"] is True
        assert services["transient"]["instantiated"] is False  # Not instantiated

    def test_clear_removes_cached_singletons(self):
        """Test clear() removes cached instances but keeps registrations"""
        container = ServiceContainer()
        call_count = [0]

        def factory(c):
            call_count[0] += 1
            return f"instance_{call_count[0]}"

        container.register("service", factory, singleton=True)

        # First get
        instance1 = container.get("service")
        assert instance1 == "instance_1"
        assert call_count[0] == 1

        # Clear cache
        container.clear()

        # Second get creates new instance
        instance2 = container.get("service")
        assert instance2 == "instance_2"
        assert call_count[0] == 2

        # Service still registered
        assert container.has("service")

    def test_override_replaces_instance(self):
        """Test override() replaces service instance"""
        container = ServiceContainer()
        container.register("service", lambda c: "original")

        # Get original
        original = container.get("service")
        assert original == "original"

        # Override with mock
        container.override("service", "mocked")
        overridden = container.get("service")
        assert overridden == "mocked"

    def test_override_unregistered_raises_error(self):
        """Test overriding unregistered service raises KeyError"""
        container = ServiceContainer()

        with pytest.raises(KeyError, match="not registered"):
            container.override("nonexistent", "value")

    def test_repr(self):
        """Test __repr__ shows container status"""
        container = ServiceContainer()
        container.register("service1", lambda c: "a")
        container.register("service2", lambda c: "b")

        # Before instantiation
        repr_str = repr(container)
        assert "registered=2" in repr_str
        assert "instantiated=0" in repr_str

        # After instantiation
        container.get("service1")
        repr_str = repr(container)
        assert "registered=2" in repr_str
        assert "instantiated=1" in repr_str


class TestRealWorldScenarios:
    """Test realistic usage scenarios"""

    def test_mock_dependencies_in_tests(self):
        """Test using override() to mock dependencies in tests"""
        container = ServiceContainer()

        # Register production services
        container.register("database", lambda c: {"type": "production_db"})
        container.register("cache", lambda c: {"type": "redis", "db": c.get("database")})

        # Override database with mock for testing
        container.override("database", {"type": "mock_db"})

        # Cache now uses mock database
        cache = container.get("cache")
        assert cache["db"]["type"] == "mock_db"

    def test_multiple_services_with_shared_dependency(self):
        """Test multiple services sharing same singleton dependency"""
        container = ServiceContainer()

        # Shared config (singleton)
        container.register("config", lambda c: {"api_key": "secret123"})

        # Multiple services use same config
        container.register("service_a", lambda c: {"config": c.get("config"), "name": "A"})
        container.register("service_b", lambda c: {"config": c.get("config"), "name": "B"})

        service_a = container.get("service_a")
        service_b = container.get("service_b")

        # Both use same config instance
        assert service_a["config"] is service_b["config"]
        assert service_a["config"]["api_key"] == "secret123"

    def test_lazy_initialization(self):
        """Test services are only created when requested"""
        container = ServiceContainer()
        call_counts = {"expensive": 0, "cheap": 0}

        def expensive_factory(c):
            call_counts["expensive"] += 1
            return "expensive_resource"

        def cheap_factory(c):
            call_counts["cheap"] += 1
            return "cheap_resource"

        container.register("expensive", expensive_factory)
        container.register("cheap", cheap_factory)

        # Neither called yet
        assert call_counts["expensive"] == 0
        assert call_counts["cheap"] == 0

        # Request cheap only
        container.get("cheap")
        assert call_counts["cheap"] == 1
        assert call_counts["expensive"] == 0  # Not initialized

    def test_factory_function_receives_container(self):
        """Test factory functions receive container for dependency resolution"""
        container = ServiceContainer()

        # Service that checks container type
        def factory(c):
            assert isinstance(c, ServiceContainer)
            assert c.has("test_service")
            return "success"

        container.register("test_service", factory)
        result = container.get("test_service")
        assert result == "success"
