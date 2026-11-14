"""Merge records from different sources into one record per publication."""
from .models import record_key


def _author_key(a):
    return a["orcid"] or (a["name"] or "").lower()


def merge_two(base, other):
    out = dict(base)
    out["conflicts"] = {k: list(v) for k, v in base["conflicts"].items()}
    for field in ("doi", "title", "year"):
        if not out[field]:
            out[field] = other[field]
        elif other[field] and other[field] != out[field]:
            seen = out["conflicts"].setdefault(field, [out[field]])
            if other[field] not in seen:
                seen.append(other[field])
    authors = {_author_key(a): a for a in base["authors"] if _author_key(a)}
    for a in other["authors"]:
        k = _author_key(a)
        if k and k not in authors:
            authors[k] = a
    out["authors"] = list(authors.values())
    out["sources"] = sorted(set(base["sources"]) | set(other["sources"]))
    return out


def merge_records(records):
    merged = {}
    for rec in records:
        key = record_key(rec)
        merged[key] = merge_two(merged[key], rec) if key in merged else rec
    return sorted(merged.values(), key=record_key)
