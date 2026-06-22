"""Generate an Argon2id hash for a password, to put in AUTH_PASSWORD_HASH.

Usage:
    uv run python -m app.hash_password
    uv run python -m app.hash_password "my secret password"
"""
import getpass
import sys

from argon2 import PasswordHasher


def main() -> None:
    password = sys.argv[1] if len(sys.argv) > 1 else getpass.getpass("Password: ")
    print(PasswordHasher().hash(password))


if __name__ == "__main__":
    main()
