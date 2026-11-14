from scholar_ingest.merge import merge_records
from scholar_ingest.models import make_record
from scholar_ingest.validate import check_quality, compare_to_reference

A = {"name": "Ada", "orcid": "0000-0001-2345-6789"}
B = {"name": "Ben", "orcid": None}


def test_merge_dedupes_and_unions():
    r1 = make_record("10.1/x", "T", 2020, [A], "openalex")
    r2 = make_record("https://doi.org/10.1/X", "T", 2020, [A, B], "pubmed")
    out = merge_records([r1, r2])
    assert len(out) == 1
    assert out[0]["sources"] == ["openalex", "pubmed"]
    assert [a["name"] for a in out[0]["authors"]] == ["Ada", "Ben"]
    assert out[0]["conflicts"] == {}


def test_merge_fills_missing_and_flags_conflicts():
    r1 = make_record("10.1/x", None, 2020, [], "openalex")
    r2 = make_record("10.1/x", "Title", 2021, [], "pubmed")
    out = merge_records([r1, r2])[0]
    assert out["title"] == "Title"
    assert out["year"] == 2020 and out["conflicts"] == {"year": [2020, 2021]}


def test_records_without_doi_merge_on_title_and_year():
    r1 = make_record(None, "Same Title", 2019, [], "pubmed")
    r2 = make_record(None, "same title", 2019, [], "orcid")
    assert len(merge_records([r1, r2])) == 1
    assert len(merge_records([r1, make_record(None, "Same Title", 2018, [], "orcid")])) == 2


def test_quality_checks_flag_each_problem():
    recs = [
        make_record("10.1000/ok", "Fine", 2020, [A], "openalex"),
        make_record("10.1000/bad", None, None, [], "openalex"),
        make_record("not-a-doi", "T", 1850, [A], "openalex"),
        make_record("10.1000/future", "T", 2999, [A], "openalex"),
    ]
    issues = {(i["id"], i["issue"]) for i in check_quality(recs, max_year=2027)}
    assert issues == {
        ("10.1000/bad", "missing_title"), ("10.1000/bad", "missing_year"), ("10.1000/bad", "no_authors"),
        ("not-a-doi", "year_out_of_range"), ("not-a-doi", "invalid_doi"),
        ("10.1000/future", "year_out_of_range"),
    }


def test_year_boundaries_are_inclusive():
    recs = [make_record("10.1000/lo", "T", 1900, [A], "x"), make_record("10.1000/hi", "T", 2027, [A], "x")]
    assert check_quality(recs, min_year=1900, max_year=2027) == []


def test_compare_to_reference():
    recs = [make_record("10.1/a", "T", 2020, [A], "x"), make_record("10.1/extra", "T", 2020, [A], "x")]
    out = compare_to_reference(recs, ["https://doi.org/10.1/A", "10.1/missing"])
    assert out == {"missing": ["10.1/missing"], "unexpected": ["10.1/extra"], "coverage": 0.5}
    assert compare_to_reference(recs, [])["coverage"] == 0.0


def test_missing_value_in_other_record_is_not_a_conflict():
    r1 = make_record("10.1000/m", "Title", 2020, [A], "openalex")
    r2 = make_record("10.1000/m", None, None, [], "orcid")
    out = merge_records([r1, r2])[0]
    assert out["conflicts"] == {} and out["title"] == "Title" and out["year"] == 2020


def test_authors_without_name_or_orcid_are_ignored():
    r1 = make_record("10.1000/n", "T", 2020, [A], "openalex")
    r2 = make_record("10.1000/n", "T", 2020, [{"name": None, "orcid": None}], "orcid")
    assert [a["name"] for a in merge_records([r1, r2])[0]["authors"]] == ["Ada"]
