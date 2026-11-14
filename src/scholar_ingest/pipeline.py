"""End-to-end ingestion: fetch -> normalise -> merge -> enrich -> store."""
from .merge import merge_records
from .sources import fetch_crossref, fetch_openalex, fetch_orcid, fetch_pubmed


def run_ingestion(client, ror, store, max_pages=1, pubmed_term=None, orcids=(), enrich=True, openalex_key=None):
    records = fetch_openalex(
        client, ror, max_pages=max_pages, api_key=openalex_key)
    if pubmed_term:
        records += fetch_pubmed(client, pubmed_term)
    for orcid in orcids:
        records += fetch_orcid(client, orcid)
    merged = merge_records(records)

    if enrich:
        extra = []
        for r in merged:
            incomplete = not (r["title"] and r["year"] and r["authors"])
            if r["doi"] and incomplete:
                cr = fetch_crossref(client, r["doi"])
                if cr:
                    extra.append(cr)
        merged = merge_records(merged + extra)

    store.upsert_many(merged)
    return merged
