from fixtures import *  # noqa
from scholar_ingest import sources


def test_openalex_paginates_and_parses():
    c = FakeClient()
    recs = sources.fetch_openalex(c, "https://ror.org/x", max_pages=5)
    assert len(recs) == 3
    assert [call[1]["cursor"] for call in c.calls] == ["*", "cursor-2"]  # stops when cursor is None
    first = recs[0]
    assert first["doi"] == "10.1000/a" and first["year"] == 2020
    assert first["authors"][0] == {"name": "Ada Example", "orcid": "0000-0001-2345-6789"}


def test_openalex_respects_max_pages():
    c = FakeClient()
    assert len(sources.fetch_openalex(c, "r", max_pages=1)) == 2
    assert len(c.calls) == 1


def test_crossref_parse():
    rec = sources.parse_crossref(CROSSREF_B["message"])
    assert (rec["doi"], rec["title"], rec["year"]) == ("10.1000/b", "Beta Results", 2018)
    assert rec["authors"] == [{"name": "Dana Beta", "orcid": "0000-0002-1825-0097"}]


def test_crossref_404_gives_none():
    assert sources.fetch_crossref(FakeClient(), "10.1000/unknown") is None


def test_pubmed_parse_with_and_without_doi():
    recs = sources.fetch_pubmed(FakeClient(), "Saarland University[Affiliation]")
    assert recs[0]["doi"] == "10.1000/a" and recs[0]["year"] == 2021
    assert recs[1]["doi"] is None and recs[1]["year"] == 2019


def test_orcid_parse():
    rec = sources.fetch_orcid(FakeClient(), "0000-0001-2345-6789")[0]
    assert (rec["doi"], rec["title"], rec["year"]) == ("10.1000/c", "Delta Paper", 2022)
