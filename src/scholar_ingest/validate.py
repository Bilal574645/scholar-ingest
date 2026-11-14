"""Data-quality checks and comparison against what an institution really publishes."""
import datetime

from .models import DOI_RE, normalize_doi


def check_quality(records, min_year=1900, max_year=None):
    max_year = max_year or datetime.date.today().year + 1
    issues = []
    for r in records:
        ident = r.get("doi") or r.get("title")
        if not r.get("title"):
            issues.append({"id": ident, "issue": "missing_title"})
        if not r.get("year"):
            issues.append({"id": ident, "issue": "missing_year"})
        elif not (min_year <= r["year"] <= max_year):
            issues.append({"id": ident, "issue": "year_out_of_range"})
        if not r.get("authors"):
            issues.append({"id": ident, "issue": "no_authors"})
        if r.get("doi") and not DOI_RE.match(r["doi"]):
            issues.append({"id": ident, "issue": "invalid_doi"})
        for field in r.get("conflicts", {}):
            issues.append({"id": ident, "issue": f"conflict_{field}"})
    return issues


def compare_to_reference(records, reference_dois):
    """Compare ingested DOIs with a reference list (e.g. copied from the institution's own publication page)."""
    got = {r["doi"] for r in records if r.get("doi")}
    ref = {normalize_doi(d) for d in reference_dois if normalize_doi(d)}
    return {
        "missing": sorted(ref - got),
        "unexpected": sorted(got - ref),
        "coverage": round(len(got & ref) / len(ref), 3) if ref else 0.0,
    }
