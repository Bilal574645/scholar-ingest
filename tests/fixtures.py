"""Hand-written API payloads that mimic the real response shapes (no network needed)."""

OPENALEX_PAGE_1 = {
    "meta": {"next_cursor": "cursor-2"},
    "results": [
        {"doi": "https://doi.org/10.1000/A", "title": "Alpha Study", "publication_year": 2020,
         "authorships": [
             {"author": {"display_name": "Ada Example", "orcid": "https://orcid.org/0000-0001-2345-6789"}},
             {"author": {"display_name": "Ben Sample", "orcid": None}}]},
        {"doi": "https://doi.org/10.1000/b", "title": None, "publication_year": None, "authorships": []},
    ],
}
OPENALEX_PAGE_2 = {
    "meta": {"next_cursor": None},
    "results": [  # same paper as W1 with a different DOI spelling -> must be de-duplicated
        {"doi": "10.1000/a", "title": "Alpha Study", "publication_year": 2020,
         "authorships": [{"author": {"display_name": "Cleo Third", "orcid": None}}]},
    ],
}
CROSSREF_B = {"message": {"DOI": "10.1000/B", "title": ["Beta Results"], "issued": {"date-parts": [[2018, 5]]},
                          "author": [{"given": "Dana", "family": "Beta", "ORCID": "http://orcid.org/0000-0002-1825-0097"}]}}
PUBMED_SEARCH = {"esearchresult": {"idlist": ["111", "222"]}}
PUBMED_SUMMARY = {"result": {
    "uids": ["111", "222"],
    "111": {"title": "Alpha Study", "pubdate": "2021 Mar", "authors": [{"name": "Example A"}],
            "articleids": [{"idtype": "pubmed", "value": "111"}, {"idtype": "doi", "value": "10.1000/a"}]},
    "222": {"title": "Gamma Notes", "pubdate": "2019", "authors": [{"name": "Gina Gamma"}], "articleids": []},
}}
ORCID_WORKS = {"group": [{"work-summary": [{
    "title": {"title": {"value": "Delta Paper"}},
    "publication-date": {"year": {"value": "2022"}},
    "external-ids": {"external-id": [{"external-id-type": "doi", "external-id-value": "10.1000/C"}]}}]}]}


class FakeClient:
    """Routes URLs to the fixtures above; records every call for assertions."""
    def __init__(self):
        self.calls = []

    def get_json(self, url, params=None, headers=None):
        self.calls.append((url, params))
        if "openalex" in url:
            return OPENALEX_PAGE_1 if params["cursor"] == "*" else OPENALEX_PAGE_2
        if "crossref" in url:
            return CROSSREF_B if url.endswith("10.1000/b") else None
        if "esearch" in url:
            return PUBMED_SEARCH
        if "esummary" in url:
            return PUBMED_SUMMARY
        if "orcid" in url:
            return ORCID_WORKS
        raise AssertionError(f"unexpected URL {url}")
