"""Tests for naming convention compliance."""

import ast
import re
from pathlib import Path
from typing import List, Tuple

import pytest


def get_python_files(directory: str) -> List[Path]:
    """Get all Python files in a directory recursively."""
    path = Path(directory)
    return list(path.rglob("*.py"))


def get_class_names(file_path: Path) -> List[str]:
    """Extract all class names from a Python file."""
    class_names = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_names.append(node.name)

    except (SyntaxError, UnicodeDecodeError):
        pass

    return class_names


def get_function_names(file_path: Path) -> List[Tuple[str, bool]]:
    """Extract all function names from a Python file with whether they're in a class."""
    functions = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        # Get top-level functions
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                functions.append((node.name, False))
            elif isinstance(node, ast.ClassDef):
                # Get methods inside the class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        functions.append((item.name, True))

    except (SyntaxError, UnicodeDecodeError):
        pass

    return functions


class TestServiceNaming:
    """Tests for service class naming conventions."""

    def test_services_end_with_service(self):
        """Service classes must end with 'Service'."""
        service_files = get_python_files("src/dashboard/services")
        violations = []

        # Exclude base classes, protocols, dataclasses
        excluded_patterns = ["Protocol", "Backend", "Policy", "Container", "Entry", "Stats"]

        for file_path in service_files:
            if file_path.name == "__init__.py":
                continue

            class_names = get_class_names(file_path)

            for class_name in class_names:
                # Skip excluded patterns (dataclasses, protocols, etc.)
                if any(pattern in class_name for pattern in excluded_patterns):
                    continue

                # Skip private classes
                if class_name.startswith("_"):
                    continue

                if not class_name.endswith("Service"):
                    violations.append(f"{file_path.name}: {class_name}")

        assert not violations, f"Service classes must end with 'Service':\n" + "\n".join(violations)


class TestDTONaming:
    """Tests for DTO class naming conventions."""

    def test_dtos_end_with_dto(self):
        """DTO classes must end with 'DTO'."""
        dto_files = get_python_files("src/dashboard/dtos")
        violations = []

        # Exclude base DTO class itself
        excluded_classes = ["BaseDTO"]

        for file_path in dto_files:
            if file_path.name == "__init__.py":
                continue

            class_names = get_class_names(file_path)

            for class_name in class_names:
                if class_name in excluded_classes:
                    continue

                # Skip private classes
                if class_name.startswith("_"):
                    continue

                if not class_name.endswith("DTO"):
                    violations.append(f"{file_path.name}: {class_name}")

        assert not violations, f"DTO classes must end with 'DTO':\n" + "\n".join(violations)


class TestBlueprintNaming:
    """Tests for blueprint naming conventions."""

    def test_blueprint_files_use_snake_case(self):
        """Blueprint files must use snake_case naming."""
        blueprint_files = get_python_files("src/dashboard/blueprints")
        violations = []

        for file_path in blueprint_files:
            if file_path.name == "__init__.py":
                continue

            filename = file_path.stem
            # Check if filename is snake_case (lowercase with underscores)
            if not re.match(r"^[a-z][a-z0-9_]*$", filename):
                violations.append(f"{file_path.name} (should be snake_case)")

        assert not violations, f"Blueprint files must use snake_case:\n" + "\n".join(violations)

    def test_blueprint_routes_use_kebab_case(self):
        """Blueprint route decorators should use kebab-case for multi-word paths."""
        blueprint_files = get_python_files("src/dashboard/blueprints")
        violations = []

        for file_path in blueprint_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Find route decorators
                route_patterns = re.findall(r'@\w+\.route\(["\']([^"\']+)["\']\)', content)

                for route in route_patterns:
                    # Skip variable routes like <username>
                    if "<" in route:
                        continue

                    # Skip root and single-word routes
                    if route == "/" or "/" not in route.strip("/"):
                        continue

                    # Check each path segment
                    segments = [s for s in route.split("/") if s]
                    for segment in segments:
                        # Check if segment contains uppercase or underscore
                        if "_" in segment or any(c.isupper() for c in segment):
                            violations.append(f"{file_path.name}: {route}")
                            break

            except (UnicodeDecodeError, IOError):
                pass

        assert not violations, f"Blueprint routes should use kebab-case:\n" + "\n".join(violations)


class TestModelNaming:
    """Tests for model/domain class naming conventions."""

    def test_model_classes_use_pascal_case(self):
        """Domain model classes must use PascalCase."""
        model_files = get_python_files("src/models")
        violations = []

        for file_path in model_files:
            if file_path.name == "__init__.py":
                continue

            class_names = get_class_names(file_path)

            for class_name in class_names:
                # Skip private classes
                if class_name.startswith("_"):
                    continue

                # Check if PascalCase (starts with uppercase, no underscores)
                if not re.match(r"^[A-Z][a-zA-Z0-9]*$", class_name):
                    violations.append(f"{file_path.name}: {class_name}")

        assert not violations, f"Model classes must use PascalCase:\n" + "\n".join(violations)


class TestFunctionNaming:
    """Tests for function naming conventions."""

    def test_public_functions_use_snake_case(self):
        """Public functions must use snake_case."""
        # Check all Python files in src/
        all_files = get_python_files("src")
        violations = []

        # Known exceptions for methods inherited from stdlib
        # (e.g., logging.Handler.doRollover)
        stdlib_method_exceptions = {"doRollover", "emit", "shouldRollover"}

        for file_path in all_files:
            functions = get_function_names(file_path)

            for func_name, is_method in functions:
                # Skip private functions/methods
                if func_name.startswith("_"):
                    continue

                # Skip special methods
                if func_name.startswith("__") and func_name.endswith("__"):
                    continue

                # Skip stdlib method overrides
                if func_name in stdlib_method_exceptions:
                    continue

                # Check if snake_case
                if not re.match(r"^[a-z][a-z0-9_]*$", func_name):
                    violations.append(f"{file_path.relative_to('src')}: {func_name}")

        # Only show first 10 violations to avoid overwhelming output
        if len(violations) > 10:
            violations = violations[:10] + [f"... and {len(violations) - 10} more"]

        assert not violations, f"Public functions must use snake_case:\n" + "\n".join(violations)


class TestFileNaming:
    """Tests for file naming conventions."""

    def test_python_files_use_snake_case(self):
        """Python files must use snake_case naming."""
        # Check all Python files in src/
        all_files = get_python_files("src")
        violations = []

        for file_path in all_files:
            if file_path.name == "__init__.py":
                continue

            filename = file_path.stem
            # Check if filename is snake_case (lowercase with underscores)
            if not re.match(r"^[a-z][a-z0-9_]*$", filename):
                violations.append(str(file_path.relative_to("src")))

        assert not violations, f"Python files must use snake_case:\n" + "\n".join(violations)


class TestConstantNaming:
    """Tests for constant naming conventions."""

    def test_module_constants_use_upper_snake_case(self):
        """Module-level constants should use UPPER_SNAKE_CASE."""
        # We'll parse constants defined at module level
        all_files = get_python_files("src")
        violations = []

        for file_path in all_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(file_path))

                # Get module-level assignments
                for node in tree.body:
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                name = target.id

                                # Skip private variables
                                if name.startswith("_"):
                                    continue

                                # Skip if it looks like a type annotation or variable
                                if name[0].islower():
                                    continue

                                # If it starts with uppercase, check if UPPER_SNAKE_CASE
                                if name[0].isupper() and not re.match(r"^[A-Z][A-Z0-9_]*$", name):
                                    violations.append(f"{file_path.relative_to('src')}: {name}")

            except (SyntaxError, UnicodeDecodeError):
                pass

        # Limit output
        if len(violations) > 10:
            violations = violations[:10] + [f"... and {len(violations) - 10} more"]

        assert not violations, f"Module constants should use UPPER_SNAKE_CASE:\n" + "\n".join(violations)
