"""Tests for layer dependency rules in Clean Architecture."""

import ast
import os
from pathlib import Path
from typing import List, Set

import pytest


def get_python_files(directory: str) -> List[Path]:
    """Get all Python files in a directory recursively."""
    path = Path(directory)
    return list(path.rglob("*.py"))


def get_imports(file_path: Path) -> Set[str]:
    """Extract all import statements from a Python file."""
    imports = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])

    except (SyntaxError, UnicodeDecodeError) as e:
        pytest.fail(f"Failed to parse {file_path}: {e}")

    return imports


def get_full_module_imports(file_path: Path) -> Set[str]:
    """Extract all import module paths (not just first component)."""
    imports = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)

    except (SyntaxError, UnicodeDecodeError):
        pass

    return imports


class TestDomainLayerDependencies:
    """Tests for Domain layer (src/models/) dependency rules."""

    def test_domain_has_no_infrastructure_imports(self):
        """Domain layer must not import from Infrastructure layer."""
        domain_files = get_python_files("src/models")
        violations = []

        for file_path in domain_files:
            imports = get_full_module_imports(file_path)

            # Check for infrastructure imports
            infrastructure_imports = [
                imp
                for imp in imports
                if imp.startswith("src.collectors")
                or imp.startswith("src.utils")
                and not imp.startswith("src.utils.date_ranges")
            ]

            if infrastructure_imports:
                violations.append(f"{file_path}: {infrastructure_imports}")

        assert not violations, f"Domain layer must not import Infrastructure:\n" + "\n".join(violations)

    def test_domain_has_no_presentation_imports(self):
        """Domain layer must not import from Presentation layer."""
        domain_files = get_python_files("src/models")
        violations = []

        for file_path in domain_files:
            imports = get_full_module_imports(file_path)

            # Check for presentation imports
            presentation_imports = [
                imp for imp in imports if imp.startswith("src.dashboard.blueprints") or imp.startswith("flask")
            ]

            if presentation_imports:
                violations.append(f"{file_path}: {presentation_imports}")

        assert not violations, f"Domain layer must not import Presentation:\n" + "\n".join(violations)

    def test_domain_has_no_application_imports(self):
        """Domain layer must not import from Application layer."""
        domain_files = get_python_files("src/models")
        violations = []

        for file_path in domain_files:
            imports = get_full_module_imports(file_path)

            # Check for application service imports
            application_imports = [imp for imp in imports if imp.startswith("src.dashboard.services")]

            if application_imports:
                violations.append(f"{file_path}: {application_imports}")

        assert not violations, f"Domain layer must not import Application services:\n" + "\n".join(violations)


class TestPresentationLayerDependencies:
    """Tests for Presentation layer (src/dashboard/blueprints/) dependency rules."""

    def test_presentation_does_not_import_domain_directly(self):
        """Presentation layer must not import Domain layer directly."""
        presentation_files = get_python_files("src/dashboard/blueprints")
        violations = []

        for file_path in presentation_files:
            imports = get_full_module_imports(file_path)

            # Check for direct domain imports (excluding DTOs)
            domain_imports = [imp for imp in imports if imp.startswith("src.models")]

            if domain_imports:
                violations.append(f"{file_path}: {domain_imports}")

        assert not violations, f"Presentation must not import Domain directly:\n" + "\n".join(violations)

    def test_presentation_does_not_import_infrastructure(self):
        """Presentation layer must not import Infrastructure layer."""
        presentation_files = get_python_files("src/dashboard/blueprints")
        violations = []

        # Known acceptable exceptions
        acceptable_exceptions = [
            "src.utils.performance",  # Performance monitoring (Phase 4.1 Adapter pattern)
        ]

        for file_path in presentation_files:
            imports = get_full_module_imports(file_path)

            # Check for infrastructure imports
            infrastructure_imports = [
                imp
                for imp in imports
                if (imp.startswith("src.collectors") or imp.startswith("src.utils"))
                and imp not in acceptable_exceptions
            ]

            if infrastructure_imports:
                violations.append(f"{file_path}: {infrastructure_imports}")

        assert not violations, f"Presentation must not import Infrastructure:\n" + "\n".join(violations)


class TestApplicationLayerDependencies:
    """Tests for Application layer (src/dashboard/services/) dependency rules."""

    def test_application_does_not_import_presentation(self):
        """Application layer must not import Presentation layer."""
        application_files = get_python_files("src/dashboard/services")
        violations = []

        for file_path in application_files:
            imports = get_full_module_imports(file_path)

            # Check for presentation imports
            presentation_imports = [imp for imp in imports if imp.startswith("src.dashboard.blueprints")]

            if presentation_imports:
                violations.append(f"{file_path}: {presentation_imports}")

        assert not violations, f"Application must not import Presentation:\n" + "\n".join(violations)


class TestInfrastructureLayerDependencies:
    """Tests for Infrastructure layer (src/collectors/, src/utils/) dependency rules."""

    def test_infrastructure_does_not_import_presentation(self):
        """Infrastructure layer must not import Presentation layer."""
        infrastructure_files = get_python_files("src/collectors") + get_python_files("src/utils")
        violations = []

        for file_path in infrastructure_files:
            imports = get_full_module_imports(file_path)

            # Check for presentation imports
            presentation_imports = [imp for imp in imports if imp.startswith("src.dashboard.blueprints")]

            if presentation_imports:
                violations.append(f"{file_path}: {presentation_imports}")

        assert not violations, f"Infrastructure must not import Presentation:\n" + "\n".join(violations)

    def test_infrastructure_does_not_import_application(self):
        """Infrastructure layer must not import Application services."""
        infrastructure_files = get_python_files("src/collectors") + get_python_files("src/utils")
        violations = []

        for file_path in infrastructure_files:
            imports = get_full_module_imports(file_path)

            # Check for application service imports
            application_imports = [imp for imp in imports if imp.startswith("src.dashboard.services")]

            if application_imports:
                violations.append(f"{file_path}: {application_imports}")

        assert not violations, f"Infrastructure must not import Application:\n" + "\n".join(violations)


class TestCircularDependencies:
    """Tests for detecting circular dependencies between layers."""

    def test_no_circular_dependencies_between_layers(self):
        """Ensure no circular dependencies exist between architectural layers."""
        # This is a comprehensive test that checks the entire dependency graph
        layers = {
            "Domain": get_python_files("src/models"),
            "Application": get_python_files("src/dashboard/services"),
            "Presentation": get_python_files("src/dashboard/blueprints"),
            "Infrastructure": get_python_files("src/collectors") + get_python_files("src/utils"),
        }

        # Build dependency graph
        dependencies = {}
        for layer_name, files in layers.items():
            layer_deps = set()
            for file_path in files:
                imports = get_full_module_imports(file_path)
                for imp in imports:
                    if imp.startswith("src.models"):
                        layer_deps.add("Domain")
                    elif imp.startswith("src.dashboard.services"):
                        layer_deps.add("Application")
                    elif imp.startswith("src.dashboard.blueprints"):
                        layer_deps.add("Presentation")
                    elif imp.startswith("src.collectors") or imp.startswith("src.utils"):
                        layer_deps.add("Infrastructure")

            dependencies[layer_name] = layer_deps - {layer_name}  # Remove self-references

        # Check for circular dependencies
        def has_circular_path(start, current, visited, path):
            if current in visited:
                if current == start and len(path) > 1:
                    return True, path
                return False, []

            visited.add(current)
            path.append(current)

            for dep in dependencies.get(current, set()):
                has_cycle, cycle_path = has_circular_path(start, dep, visited.copy(), path.copy())
                if has_cycle:
                    return True, cycle_path

            return False, []

        violations = []
        for layer in layers.keys():
            has_cycle, cycle = has_circular_path(layer, layer, set(), [])
            if has_cycle:
                violations.append(f"Circular dependency: {' -> '.join(cycle)}")

        assert not violations, f"Circular dependencies detected:\n" + "\n".join(violations)
