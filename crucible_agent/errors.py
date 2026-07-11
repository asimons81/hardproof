"""Typed errors returned safely across Crucible boundaries."""


class CrucibleError(Exception):
    """Base class for expected Crucible failures."""


class ValidationError(CrucibleError, ValueError):
    """A supplied value violates a protocol contract."""


class TransitionError(CrucibleError):
    """A requested stage transition cannot pass its gates."""
