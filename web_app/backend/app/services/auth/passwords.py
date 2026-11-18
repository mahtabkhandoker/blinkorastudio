"""Password hashing — argon2id via the maintained `argon2-cffi` library.

Never swap this for a fast general-purpose hash (sha256, md5, ...); argon2
is deliberately slow and memory-hard so an offline dictionary attack on a
leaked `password_hash` column is expensive.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True if the hash was made with older/weaker parameters than the
    hasher's current defaults; callers may re-hash on next successful login."""
    return _hasher.check_needs_rehash(password_hash)
