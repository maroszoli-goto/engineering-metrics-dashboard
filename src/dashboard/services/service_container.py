"""Service Container for Dependency Injection

Provides a lightweight dependency injection container for managing service
instances and their dependencies. Supports both singleton and transient
(new instance per request) service lifetimes.

Example:
    >>> container = ServiceContainer()
    >>> container.register("config", lambda c: load_config())
    >>> container.register("cache", lambda c: CacheService(c.get("config")))
    >>> cache = container.get("cache")  # Auto-resolves config dependency
"""

from typing import Any, Callable, Dict, Optional, Set


class ServiceContainer:
    """Dependency injection container for services

    Features:
    - Factory-based service registration
    - Singleton and transient lifetimes
    - Automatic dependency resolution
    - Circular dependency detection
    - Clear error messages
    """

    def __init__(self):
        """Initialize empty service container"""
        self._services: Dict[str, Any] = {}  # Cached singleton instances
        self._factories: Dict[str, Dict[str, Any]] = {}  # Service factories
        self._resolving: Set[str] = set()  # Track circular dependencies

    def register(
        self,
        name: str,
        factory: Callable[["ServiceContainer"], Any],
        singleton: bool = True,
    ) -> None:
        """Register a service factory

        Args:
            name: Service identifier (e.g., 'cache_service', 'config')
            factory: Callable that takes container and returns service instance
            singleton: If True, cache instance; if False, create new each time

        Example:
            >>> container.register(
            ...     "cache",
            ...     lambda c: CacheService(data_dir=Path("data")),
            ...     singleton=True
            ... )

        Raises:
            ValueError: If service name already registered
        """
        if name in self._factories:
            raise ValueError(f"Service '{name}' is already registered")

        self._factories[name] = {
            "factory": factory,
            "singleton": singleton,
        }

    def get(self, name: str) -> Any:
        """Get a service instance

        Resolves dependencies automatically by calling the factory function.
        For singletons, caches the instance after first creation.

        Args:
            name: Service identifier

        Returns:
            Service instance

        Example:
            >>> cache_service = container.get("cache_service")
            >>> config = container.get("config")

        Raises:
            KeyError: If service not registered
            RuntimeError: If circular dependency detected
        """
        # Return cached singleton if available
        if name in self._services:
            return self._services[name]

        # Check if service registered
        if name not in self._factories:
            registered = ", ".join(sorted(self._factories.keys()))
            raise KeyError(f"Service '{name}' not registered. " f"Available services: {registered or 'none'}")

        # Detect circular dependencies
        if name in self._resolving:
            chain = " -> ".join(sorted(self._resolving))
            raise RuntimeError(
                f"Circular dependency detected: {chain} -> {name}. "
                f"Check your service factory functions for circular references."
            )

        # Resolve service
        self._resolving.add(name)
        try:
            factory_info = self._factories[name]
            factory = factory_info["factory"]

            # Call factory to create instance
            instance = factory(self)

            # Cache if singleton
            if factory_info["singleton"]:
                self._services[name] = instance

            return instance
        finally:
            self._resolving.discard(name)

    def has(self, name: str) -> bool:
        """Check if service is registered

        Args:
            name: Service identifier

        Returns:
            True if service registered, False otherwise

        Example:
            >>> if container.has("redis"):
            ...     redis = container.get("redis")
        """
        return name in self._factories

    def clear(self) -> None:
        """Clear all cached singleton instances

        Useful for testing to ensure fresh instances.
        Does not clear factory registrations.

        Example:
            >>> container.clear()  # All singletons will be re-created on next get()
        """
        self._services.clear()

    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """List all registered services

        Returns:
            Dictionary mapping service name to metadata:
            - singleton: Whether service is singleton
            - instantiated: Whether instance has been created

        Example:
            >>> services = container.list_services()
            >>> print(services["cache_service"])
            {'singleton': True, 'instantiated': True}
        """
        result = {}
        for name, factory_info in self._factories.items():
            result[name] = {
                "singleton": factory_info["singleton"],
                "instantiated": name in self._services,
            }
        return result

    def override(self, name: str, instance: Any) -> None:
        """Override a service instance (useful for testing)

        Replaces the cached instance for a service without changing
        its factory registration. Useful for injecting mocks in tests.

        Args:
            name: Service identifier
            instance: Mock or test instance

        Example:
            >>> mock_cache = Mock(spec=CacheService)
            >>> container.override("cache_service", mock_cache)
            >>> # Now container.get("cache_service") returns mock

        Raises:
            KeyError: If service not registered
        """
        if name not in self._factories:
            raise KeyError(
                f"Cannot override '{name}' - service not registered. " f"Register it first with container.register()"
            )

        self._services[name] = instance

    def __repr__(self) -> str:
        """String representation of container"""
        num_registered = len(self._factories)
        num_instantiated = len(self._services)
        return f"ServiceContainer(" f"registered={num_registered}, " f"instantiated={num_instantiated})"
