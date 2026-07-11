"""Typed errors returned safely across Hardproof boundaries."""


class HardproofError(Exception):
    """Base class for expected Hardproof failures."""


class ValidationError(HardproofError, ValueError):
    """A supplied value violates a protocol contract."""


class TransitionError(HardproofError):
    """A requested stage transition cannot pass its gates."""
