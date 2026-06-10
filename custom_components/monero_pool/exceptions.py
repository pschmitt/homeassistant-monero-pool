"""Exceptions for the Monero Pool integration."""

from __future__ import annotations


class MoneroPoolError(Exception):
    """Base error for Monero pool clients."""


class MoneroPoolConnectionError(MoneroPoolError):
    """Raised when a pool or proxy endpoint cannot be reached."""


class MoneroPoolAuthError(MoneroPoolError):
    """Raised when authentication fails."""

