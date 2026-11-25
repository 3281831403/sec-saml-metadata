"""Core metadata lifecycle contract.

The eight operations below implement the federated metadata lifecycle.  The
numbered sections repair the ten defects described in README.md, in the same
order the defects are listed there.
"""

import hashlib
import hmac
import json


# --- parsing ---------------------------------------------------------------


def parse_metadata(text) -> dict:
    """Parse the JSON text form of a metadata document."""
    return json.loads(text)


# --- defect 02 + defect 03: validity window and skew applied exactly once --


def check_validity(metadata, now, skew) -> bool:
    """Return True when ``now`` falls inside the closed validity window.

    The skew relaxes only the lower bound and is subtracted exactly once:
    the window is ``[valid_from - skew, valid_until]``.  A document past
    ``valid_until`` is always rejected, regardless of the skew.
    """
    return metadata["valid_from"] - skew <= now <= metadata["valid_until"]


# --- defect 01 + defect 10: signature coverage and constant-time compare --


def _canonical_payload(metadata) -> bytes:
    body = {
        "entity_id": metadata["entity_id"],
        "keys": metadata["keys"],
    }
    return json.dumps(
        body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def check_signature(metadata, key) -> bool:
    """Verify the HMAC-SHA256 signature over entity_id and keys.

    The signature is only accepted when ``covered`` declares both
    ``entity_id`` and ``keys`` (defect 01), the recomputed digest matches
    the carried value, and the comparison is constant-time (defect 10).
    """
    signature = metadata.get("signature")
    if not isinstance(signature, dict):
        return False

    covered = signature.get("covered")
    if not isinstance(covered, list):
        return False
    # Both fields must be declared; covering only one leaves the other
    # open to undetectable tampering.
    if "entity_id" not in covered or "keys" not in covered:
        return False

    expected = hmac.new(
        key, _canonical_payload(metadata), hashlib.sha256
    ).hexdigest()
    value = signature.get("value")
    if not isinstance(value, str):
        return False
    # hmac.compare_digest ignores overridden __eq__ on the compared object
    # and avoids the timing side channel of a plain == comparison.
    return hmac.compare_digest(expected, value)


# --- defect 04: exact, character-for-character entity id matching ----------


def check_entity_id(metadata, expected) -> bool:
    """Return True only when the entity id matches exactly.

    No prefix/suffix/contains matching and no URL normalisation: two
    similar-looking identifiers must never hit each other.
    """
    entity_id = metadata.get("entity_id")
    if not isinstance(entity_id, str) or not isinstance(expected, str):
        return False
    return entity_id == expected


# --- defect 05: refresh decided by expiry, not by mere cache presence ------


def refresh_needed(cached, now, policy) -> bool:
    """Return True when the cached metadata must be re-fetched.

    A refresh is required when the document is no longer valid (honouring
    the policy skew), when ``valid_until`` is within ``refresh_before``
    seconds, or when the cache entry has reached ``max_age``.
    """
    metadata = cached["metadata"]
    if not check_validity(metadata, now, policy.get("skew", 0)):
        return True
    if metadata["valid_until"] - now <= policy["refresh_before"]:
        return True
    if now - cached["fetched_at"] >= policy["max_age"]:
        return True
    return False


# --- defect 06: duplicate entity ids are rejected, never overwritten -------


def store(store, metadata, now) -> dict:
    """Store a metadata document, rejecting expired or duplicate entries.

    Every precondition is checked before any part of the store is touched,
    so a rejected write leaves no partial key descriptors or index rows.
    """
    if not check_validity(metadata, now, 0):
        return store

    entity_id = metadata["entity_id"]
    if entity_id in store["entities"]:
        return store

    store["entities"][entity_id] = metadata
    store["keys"][entity_id] = {
        key_descriptor["key_id"]: key_descriptor
        for key_descriptor in metadata["keys"]
    }
    for key_descriptor in metadata["keys"]:
        store["index"][key_descriptor["key_id"]] = entity_id
    return store


# --- defect 07 + defect 08: eviction clears index and key descriptors -----


def evict(store, now) -> int:
    """Remove every document whose validity has ended.

    Eviction deletes the main entity record, the key descriptors and the
    key_id index rows, and returns how many entities were removed.
    """
    expired_entities = [
        entity_id
        for entity_id, metadata in store["entities"].items()
        if now > metadata["valid_until"]
    ]

    for entity_id in expired_entities:
        metadata = store["entities"].pop(entity_id)
        store["keys"].pop(entity_id, None)
        for key_id in (
            key_descriptor["key_id"] for key_descriptor in metadata["keys"]
        ):
            # Only drop index rows that still point at this entity.
            if store["index"].get(key_id) == entity_id:
                del store["index"][key_id]

    return len(expired_entities)


# --- defect 09: each batch request is validated independently -------------


def metadata_batch(requests, policy, now) -> dict:
    """Validate a batch of requests without sharing state between them.

    Every request is parsed, checked and verified on its own; no cached
    entity from a previous request may leak into the next one.
    """
    results = {}
    for request in requests:
        metadata = parse_metadata(request["metadata"])
        results[request["request_id"]] = (
            check_validity(metadata, now, policy.get("skew", 0))
            and check_entity_id(metadata, request["expected_entity_id"])
            and check_signature(metadata, request["key"])
        )
    return results
