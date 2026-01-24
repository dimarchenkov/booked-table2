"""Generate bcrypt hash for admin password."""
from __future__ import annotations

import getpass

import bcrypt


def main() -> None:
    """Prompt for a password and print bcrypt hash."""

    password = getpass.getpass("Enter admin password: ").encode()
    hashed = bcrypt.hashpw(password, bcrypt.gensalt())
    print(hashed.decode())


if __name__ == "__main__":
    main()
