"""Golden-data test: the full pipeline on fixed inputs must reproduce a reviewed, committed result."""
import json
from pathlib import Path

from fixtures import FakeClient
from scholar_ingest.pipeline import run_ingestion
from scholar_ingest.store import JsonlStore, MemoryStore

GOLDEN = Path(__file__).parent / "golden" / "expected_merged.json"


def run():
    return run_ingestion(FakeClient(), "https://ror.org/x", MemoryStore(), max_pages=5,
                         pubmed_term="Saarland[Affiliation]", orcids=["0000-0001-2345-6789"])


def test_pipeline_matches_golden():
    assert run() == json.loads(GOLDEN.read_text())


def test_crossref_only_called_for_incomplete_records():
    c = FakeClient()
    run_ingestion(c, "r", MemoryStore(), max_pages=5)
    crossref_urls = [u for u, _ in c.calls if "crossref" in u]
    assert crossref_urls == ["https://api.crossref.org/works/10.1000/b"]


def test_enrichment_can_be_disabled():
    c = FakeClient()
    run_ingestion(c, "r", MemoryStore(), max_pages=5, enrich=False)
    assert not [u for u, _ in c.calls if "crossref" in u]


def test_jsonl_store_roundtrip_is_idempotent(tmp_path):
    store = JsonlStore(tmp_path / "r.jsonl")
    recs = run()
    store.upsert_many(recs)
    store.upsert_many(recs)  # re-running ingestion must not duplicate
    assert store.all() == recs
