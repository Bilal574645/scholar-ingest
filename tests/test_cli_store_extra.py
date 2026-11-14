import datetime
import json

from fixtures import FakeClient
from scholar_ingest import cli
from scholar_ingest.merge import merge_records
from scholar_ingest.models import make_record, record_key
from scholar_ingest.pipeline import run_ingestion
from scholar_ingest.report import render_html
from scholar_ingest.store import JsonlStore, MemoryStore, MongoStore
from scholar_ingest.validate import check_quality

AUTH = [{"name": "Ada", "orcid": None}]


# ---- validate defaults ----
def test_default_year_window_uses_current_year():
    this_year = datetime.date.today().year
    ok = [make_record("10.1000/now", "T", this_year, AUTH, "x"),
          make_record("10.1000/next", "T", this_year + 1, AUTH, "x")]
    assert check_quality(ok) == []
    too_new = [make_record("10.1000/far", "T", this_year + 2, AUTH, "x")]
    assert [i["issue"] for i in check_quality(too_new)] == [
        "year_out_of_range"]


def test_explicit_max_year_is_used():
    assert check_quality(
        [make_record("10.1000/y", "T", 2029, AUTH, "x")], max_year=2030) == []
    assert check_quality(
        [make_record("10.1000/y", "T", 2031, AUTH, "x")], max_year=2030)


def test_conflicts_become_issues():
    r = make_record("10.1000/c", "T", 2020, AUTH, "a")
    r2 = make_record("10.1000/c", "T", 2021, AUTH, "b")
    assert [i["issue"] for i in check_quality(merge_records([r, r2]))] == [
        "conflict_year"]


# ---- pipeline: enrichment trigger ----
class OneRecordClient(FakeClient):
    def __init__(self, work):
        super().__init__()
        self.work = work

    def get_json(self, url, params=None, headers=None):
        if "openalex" in url:
            return {"meta": {"next_cursor": None}, "results": [self.work]}
        self.calls.append(url)
        return None


def test_enrichment_triggers_when_any_single_field_missing():
    base = {"doi": "10.1000/z", "title": "T", "publication_year": 2020,
            "authorships": [{"author": {"display_name": "A", "orcid": None}}]}
    for field, empty in (("title", None), ("publication_year", None), ("authorships", [])):
        c = OneRecordClient({**base, field: empty})
        run_ingestion(c, "r", MemoryStore())
        assert c.calls == ["https://api.crossref.org/works/10.1000/z"], field
    c = OneRecordClient(base)
    run_ingestion(c, "r", MemoryStore())
    assert c.calls == []  # complete record -> no extra API call


# ---- models ----
def test_record_key_without_doi_uses_title_and_year():
    assert record_key(make_record(None, "My Title", 2020,
                      [], "x")) == "title:my title|2020"
    assert record_key(make_record(None, None, None, [], "x")) == "title:|None"


# ---- report ----
def test_report_placeholders_and_escaping():
    html_out = render_html([make_record(None, None, None, [], "pubmed")], [
                           {"id": "<x>", "issue": "no_authors"}])
    assert "<td>-</td><td>-</td><td>-</td><td>pubmed</td>" in html_out
    assert "&lt;x&gt;" in html_out and "coverage" not in html_out


# ---- stores ----
def test_jsonl_store_creates_parent_dirs_and_handles_missing_file(tmp_path):
    store = JsonlStore(tmp_path / "a" / "b" / "r.jsonl")
    assert store.all() == []
    store.upsert_many([make_record("10.1000/q", "T", 2020, [], "x")])
    # same key -> overwritten, not duplicated
    store.upsert_many([make_record("10.1000/q", "T2", 2020, [], "x")])
    assert [r["title"] for r in store.all()] == ["T2"]


def test_jsonl_store_keeps_previously_stored_records(tmp_path):
    store = JsonlStore(tmp_path / "r.jsonl")
    store.upsert_many([make_record("10.1000/one", "One", 2020, [], "x")])
    store.upsert_many([make_record("10.1000/two", "Two", 2020, [], "x")])
    assert sorted(r["title"] for r in store.all()) == ["One", "Two"]


class FakeCollection:
    def __init__(self):
        self.docs = {}

    def replace_one(self, flt, doc, upsert=False):
        assert upsert is True
        self.docs[flt["_id"]] = doc

    def find(self):
        return list(self.docs.values())


def test_mongo_store_upserts_by_key_and_strips_id():
    store = MongoStore.__new__(MongoStore)  # skip real connection
    store.col = FakeCollection()
    rec = make_record("10.1000/m", "T", 2020, [], "x")
    store.upsert_many([rec])
    store.upsert_many([rec])
    assert len(
        store.col.docs) == 1 and "_id" in store.col.docs["doi:10.1000/m"]
    assert store.all() == [rec]


# ---- CLI ----
def test_cli_ingest_then_check(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "HttpClient", FakeClient)
    out = tmp_path / "records.jsonl"
    cli.main(["ingest", "--ror", "https://ror.org/x",
             "--max-pages", "5", "--out", str(out)])
    assert "Ingested 2 publications" in capsys.readouterr().out
    assert len(out.read_text().splitlines()) == 2

    ref = tmp_path / "ref.txt"
    ref.write_text("10.1000/a\n10.1000/b\n10.1000/not-ingested\n")
    report = tmp_path / "out" / "report.html"
    cli.main(["check", "--records", str(out), "--reference",
             str(ref), "--report", str(report)])
    text = capsys.readouterr().out
    assert "Coverage: 66.7%" in text and "missing: 1" in text and "unexpected: 0" in text
    assert "2 records" in text and report.exists()
    assert "Coverage vs reference" in report.read_text()


def test_cli_check_without_reference(tmp_path, capsys):
    out = tmp_path / "r.jsonl"
    out.write_text(json.dumps(make_record(
        "10.1000/n", "T", 2020, AUTH, "x")) + "\n")
    cli.main(["check", "--records", str(out),
             "--report", str(tmp_path / "rep.html")])
    assert "Coverage" not in capsys.readouterr().out


def test_jsonl_store_keeps_non_ascii_readable(tmp_path):
    path = tmp_path / "r.jsonl"
    JsonlStore(path).upsert_many(
        [make_record("10.1000/u", "Béguin", 2020, [], "x")])
    assert "Béguin" in path.read_text(encoding="utf-8")
