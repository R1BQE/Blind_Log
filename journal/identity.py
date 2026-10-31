"""Stable QSO identity helpers used by the journal view."""

import json


def qso_signature(qso):
    """Serialize a QSO into a deterministic identity signature."""
    return json.dumps(qso, ensure_ascii=False, sort_keys=True, default=str)


def get_qso_keys(qsos):
    """Return stable keys with occurrence numbers for duplicate QSO records."""
    occurrences = {}
    keys = []
    for qso in qsos:
        signature = qso_signature(qso)
        occurrence = occurrences.get(signature, 0)
        occurrences[signature] = occurrence + 1
        keys.append((signature, occurrence))
    return keys


def build_source_index(keys):
    """Map each signature to its source row indices in one linear pass."""
    source_indices = {}
    for source_index, (signature, _occurrence) in enumerate(keys):
        source_indices.setdefault(signature, []).append(source_index)
    return source_indices


def find_source_index(source_indices, signature, occurrence):
    """Resolve a signature occurrence to its original journal row."""
    candidates = source_indices.get(signature, ())
    if 0 <= occurrence < len(candidates):
        return candidates[occurrence]
    return -1
