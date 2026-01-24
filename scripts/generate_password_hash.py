#!/usr/bin/env python3
"""Generate password hash for dashboard authentication.

This script generates secure password hashes using Werkzeug's PBKDF2
hashing algorithm. The generated hash can be added to config.yaml.

Usage:
    python scripts/generate_password_hash.py
    python scripts/generate_password_hash.py --password mypassword
    python scripts/generate_password_hash.py --username admin --password mypassword
"""

import argparse
import getpass
import sys

try:
    from werkzeug.security import generate_password_hash
except ImportError:
    print("Error: werkzeug is not installed. Run: pip install werkzeug", file=sys.stderr)
    sys.exit(1)


def generate_hash(password: str) -> str:
    """Generate password hash using PBKDF2-SHA256.

    Args:
        password: Plain text password

    Returns:
        Password hash string
    """
    return generate_password_hash(password, method="pbkdf2:sha256")


def main():
    parser = argparse.ArgumentParser(
        description="Generate password hash for dashboard authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive (recommended - password not visible in shell history)
  python scripts/generate_password_hash.py

  # With username
  python scripts/generate_password_hash.py --username admin

  # Non-interactive (not recommended for production - visible in history)
  python scripts/generate_password_hash.py --password mypassword

Add the generated hash to config.yaml:

  dashboard:
    auth:
      enabled: true
      users:
        - username: admin
          password_hash: pbkdf2:sha256:...
        """,
    )

    parser.add_argument("--username", "-u", help="Username (for display purposes only)")
    parser.add_argument("--password", "-p", help="Password (use interactive mode for security)")

    args = parser.parse_args()

    # Get username
    if args.username:
        username = args.username
    else:
        username = input("Username: ").strip()
        if not username:
            print("Error: Username cannot be empty", file=sys.stderr)
            sys.exit(1)

    # Get password (prefer interactive for security)
    if args.password:
        password = args.password
        print("Warning: Password provided via command line (visible in shell history)", file=sys.stderr)
    else:
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm password: ")

        if password != password_confirm:
            print("Error: Passwords do not match", file=sys.stderr)
            sys.exit(1)

    if not password:
        print("Error: Password cannot be empty", file=sys.stderr)
        sys.exit(1)

    # Generate hash
    password_hash = generate_hash(password)

    # Output results
    print("\n" + "=" * 70)
    print("Password Hash Generated Successfully")
    print("=" * 70)
    print(f"\nUsername: {username}")
    print(f"Hash: {password_hash}")
    print("\nAdd to config.yaml:")
    print("-" * 70)
    print(
        f"""
dashboard:
  auth:
    enabled: true
    users:
      - username: {username}
        password_hash: {password_hash}
"""
    )
    print("-" * 70)
    print("\nSecurity Notes:")
    print("  - Store config.yaml securely (do not commit to public repositories)")
    print("  - Use strong passwords (8+ characters, mixed case, numbers, symbols)")
    print("  - Consider using environment variables for sensitive data")
    print("  - Rotate passwords regularly")
    print()


if __name__ == "__main__":
    main()
