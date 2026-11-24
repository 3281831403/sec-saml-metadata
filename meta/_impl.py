"""Core metadata lifecycle contract.

Every public operation is an intentional stub until the ten defects described
in README.md are repaired.  This is the only implementation module.
"""


def parse_metadata(text) -> dict:
    raise NotImplementedError("parse_metadata")


def check_validity(metadata, now, skew) -> bool:
    raise NotImplementedError("check_validity")


def check_signature(metadata, key) -> bool:
    raise NotImplementedError("check_signature")


def check_entity_id(metadata, expected) -> bool:
    raise NotImplementedError("check_entity_id")


def refresh_needed(cached, now, policy) -> bool:
    raise NotImplementedError("refresh_needed")


def store(store, metadata, now) -> dict:
    raise NotImplementedError("store")


def evict(store, now) -> int:
    raise NotImplementedError("evict")


def metadata_batch(requests, policy, now) -> dict:
    raise NotImplementedError("metadata_batch")