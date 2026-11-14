"""Normalisation helpers and the common record shape shared by all sources."""
import re

DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
ORCID_RE = re.compile(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])")


def normalize_doi(value):
    if not value:
        return None
    v = value.strip().lower()
    for prefix in DOI_PREFIXES:
        if v.startswith(prefix):
            v = v[len(prefix):]
    return v or None


def normalize_orcid(value):
    if not value:
        return None
    m = ORCID_RE.search(value.upper())
    return m.group(1) if m else None


def make_record(doi, title, year, authors, source):
    return {
        "doi": normalize_doi(doi),
        "title": (title or "").strip() or None,
        "year": int(year) if year else None,
        "authors": authors or [],
        "sources": [source],
        "conflicts": {},
    }


def record_key(rec):
    """Stable identity: DOI when present, otherwise title+year."""
    if rec.get("doi"):
        return "doi:" + rec["doi"]
    return "title:{}|{}".format((rec.get("title") or "").lower(), rec.get("year"))
