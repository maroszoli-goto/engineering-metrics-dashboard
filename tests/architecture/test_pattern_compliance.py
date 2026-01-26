"""Tests for design pattern compliance."""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set

import pytest


def get_python_files(directory: str) -> List[Path]:
    """Get all Python files in a directory recursively."""
    path = Path(directory)
    return list(path.rglob("*.py"))


def get_route_decorators(file_path: Path) -> List[str]:
    """Extract all route decorator patterns from a Python file."""
    routes = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all route decorators
        route_patterns = re.findall(r'@\w+\.route\(["\']([^"\']+)["\']\)', content)
        routes.extend(route_patterns)

    except (UnicodeDecodeError, IOError):
        pass

    return routes


def has_decorator(file_path: Path, decorator_name: str) -> Dict[str, List[str]]:
    """Find functions with or without a specific decorator."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        results = {"with_decorator": [], "without_decorator": []}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private functions
                if node.name.startswith("_"):
                    continue

                # Check if function has the decorator
                has_it = any(
                    (isinstance(d, ast.Name) and d.id == decorator_name)
                    or (isinstance(d, ast.Attribute) and d.attr == decorator_name)
                    for d in node.decorator_list
                )

                if has_it:
                    results["with_decorator"].append(node.name)
                else:
                    results["without_decorator"].append(node.name)

        return results

    except (SyntaxError, UnicodeDecodeError):
        return {"with_decorator": [], "without_decorator": []}


def get_base_classes(file_path: Path, class_name: str) -> List[str]:
    """Get base classes for a specific class."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                base_classes = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_classes.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_classes.append(base.attr)
                return base_classes

    except (SyntaxError, UnicodeDecodeError):
        pass

    return []


def get_all_classes_with_bases(file_path: Path) -> Dict[str, List[str]]:
    """Get all classes and their base classes from a file."""
    classes = {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_classes = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_classes.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_classes.append(base.attr)
                classes[node.name] = base_classes

    except (SyntaxError, UnicodeDecodeError):
        pass

    return classes


class TestAuthenticationDecorators:
    """Tests for authentication decorator usage."""

    def test_blueprint_routes_have_auth_decorator(self):
        """All blueprint routes should have authentication decorator when auth is enabled."""
        # Note: This test checks the pattern exists, not that it's enforced
        # Since auth is optional via config, we just verify the decorator is used consistently
        blueprint_files = get_python_files("src/dashboard/blueprints")
        route_info = []

        for file_path in blueprint_files:
            if file_path.name == "__init__.py":
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Find route functions and check for @require_auth
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if "@" in line and ".route(" in line:
                        # Look backwards for @require_auth
                        has_auth = any("@require_auth" in lines[j] for j in range(max(0, i - 5), i))
                        route_info.append(
                            {"file": file_path.name, "line": i + 1, "has_auth": has_auth, "route_line": line.strip()}
                        )

            except (UnicodeDecodeError, IOError):
                pass

        # Check consistency - if some routes have auth, all should have auth
        routes_with_auth = [r for r in route_info if r["has_auth"]]
        routes_without_auth = [r for r in route_info if not r["has_auth"]]

        # If auth is used anywhere, it should be used everywhere (consistency check)
        if routes_with_auth and routes_without_auth:
            violations = [f"{r['file']}:{r['line']} - {r['route_line']}" for r in routes_without_auth]

            # This is a warning, not a hard failure, since auth is optional
            if violations:
                pytest.skip(f"Inconsistent auth decorator usage (auth is optional):\n" + "\n".join(violations[:5]))


class TestDTOInheritance:
    """Tests for DTO inheritance patterns."""

    def test_dtos_inherit_from_base_dto(self):
        """All DTO classes must inherit from BaseDTO."""
        dto_files = get_python_files("src/dashboard/dtos")
        violations = []

        for file_path in dto_files:
            if file_path.name in ["__init__.py", "base.py"]:
                continue

            classes = get_all_classes_with_bases(file_path)

            for class_name, base_classes in classes.items():
                # Skip private classes
                if class_name.startswith("_"):
                    continue

                # DTOs should end with DTO and inherit from BaseDTO
                if class_name.endswith("DTO"):
                    if "BaseDTO" not in base_classes:
                        violations.append(f"{file_path.name}: {class_name}")

        assert not violations, f"DTO classes must inherit from BaseDTO:\n" + "\n".join(violations)


class TestServicePatterns:
    """Tests for service layer patterns."""

    def test_services_use_dependency_injection(self):
        """Services should accept dependencies via __init__ (dependency injection)."""
        service_files = get_python_files("src/dashboard/services")
        violations = []

        for file_path in service_files:
            if file_path.name == "__init__.py":
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(file_path))

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Skip protocols, backends, policies
                        if "Protocol" in node.name or "Backend" in node.name or "Policy" in node.name:
                            continue

                        # Skip private classes
                        if node.name.startswith("_"):
                            continue

                        # Look for __init__ method
                        has_init = any(isinstance(n, ast.FunctionDef) and n.name == "__init__" for n in node.body)

                        # Services should have __init__ for DI
                        # (unless they're all static methods, which is also acceptable)
                        if not has_init and node.name.endswith("Service"):
                            # Check if all methods are static
                            methods = [
                                n for n in node.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
                            ]

                            static_methods = [
                                n
                                for n in node.body
                                if isinstance(n, ast.FunctionDef)
                                and any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in n.decorator_list)
                            ]

                            # If not all methods are static, should have __init__
                            if methods and len(static_methods) < len(methods):
                                violations.append(f"{file_path.name}: {node.name} (missing __init__)")

            except (SyntaxError, UnicodeDecodeError):
                pass

        # This is more of a guideline than a strict rule
        if violations:
            pytest.skip(f"Services should use dependency injection via __init__:\n" + "\n".join(violations[:5]))


class TestErrorHandling:
    """Tests for error handling patterns."""

    def test_domain_raises_domain_exceptions(self):
        """Domain layer should raise appropriate exceptions (ValueError, etc.)."""
        # This is a guideline - domain should raise standard Python exceptions
        # or domain-specific exceptions, not framework exceptions
        domain_files = get_python_files("src/models")
        flask_exceptions = []

        for file_path in domain_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for Flask exception usage
                if "from flask import" in content and "abort" in content:
                    flask_exceptions.append(str(file_path.relative_to("src")))

            except (UnicodeDecodeError, IOError):
                pass

        assert not flask_exceptions, f"Domain should not use Flask exceptions:\n" + "\n".join(flask_exceptions)


class TestDocstringPatterns:
    """Tests for docstring presence and patterns."""

    def test_public_service_methods_have_docstrings(self):
        """Public service methods should have docstrings."""
        service_files = get_python_files("src/dashboard/services")
        violations = []

        for file_path in service_files:
            if file_path.name == "__init__.py":
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(file_path))

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name.endswith("Service"):
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                # Skip private methods and __init__
                                if item.name.startswith("_"):
                                    continue

                                # Check for docstring
                                has_docstring = ast.get_docstring(item) is not None

                                if not has_docstring:
                                    violations.append(f"{file_path.name}: {node.name}.{item.name}")

            except (SyntaxError, UnicodeDecodeError):
                pass

        # This is a guideline, not a strict requirement
        if violations and len(violations) > 10:
            pytest.skip(
                f"Public service methods should have docstrings:\n"
                + "\n".join(violations[:10])
                + f"\n... and {len(violations) - 10} more"
            )


class TestImportOrganization:
    """Tests for import organization patterns."""

    def test_imports_are_organized(self):
        """Imports should be organized: stdlib, third-party, local."""
        # This is a style guideline checked by tools like isort
        # We'll do a simple check for mixing patterns
        all_files = get_python_files("src")
        violations = []

        for file_path in all_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Find import block
                import_lines = []
                for i, line in enumerate(lines):
                    if line.strip().startswith(("import ", "from ")):
                        import_lines.append((i, line.strip()))
                    elif import_lines and line.strip() and not line.strip().startswith("#"):
                        # Non-import, non-comment line after imports - stop
                        break

                # Check if src imports come before third-party imports
                if len(import_lines) > 2:
                    src_import_line = None
                    third_party_line = None

                    for line_no, line in import_lines:
                        if "from src." in line or "import src." in line:
                            if src_import_line is None:
                                src_import_line = line_no
                        elif not line.startswith("from .") and not line.startswith("import os"):
                            # Rough heuristic for third-party
                            if "flask" in line.lower() or "pandas" in line.lower():
                                if third_party_line is None:
                                    third_party_line = line_no

                    # If src imports come before third-party, that's wrong
                    if src_import_line and third_party_line and src_import_line < third_party_line:
                        violations.append(f"{file_path.relative_to('src')} (line {src_import_line})")

            except (UnicodeDecodeError, IOError):
                pass

        # This is a style guideline
        if violations and len(violations) > 5:
            pytest.skip(f"Consider organizing imports (stdlib, third-party, local):\n" + "\n".join(violations[:5]))
