"""Federated metadata lifecycle package."""

from .api import (
    check_entity_id,
    check_signature,
    check_validity,
    evict,
    metadata_batch,
    parse_metadata,
    refresh_needed,
    store,
)

__all__ = [
    "parse_metadata",
    "check_validity",
    "check_signature",
    "check_entity_id",
    "refresh_needed",
    "store",
    "evict",
    "metadata_batch",
]