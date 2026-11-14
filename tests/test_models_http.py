import pytest

from scholar_ingest.http import HttpClient
from scholar_ingest.models import normalize_doi, normalize_orcid


@pytest.mark.parametrize("raw", ["https://doi.org/10.1000/ABC", "doi:10.1000/abc", " 10.1000/abc ", "http://dx.doi.org/10.1000/abc"])
def test_normalize_doi_variants(raw):
    assert normalize_doi(raw) == "10.1000/abc"


def test_normalize_doi_empty():
    assert normalize_doi(None) is None and normalize_doi("  ") is None


def test_normalize_orcid():
    assert normalize_orcid("https://orcid.org/0000-0001-2345-678x") == "0000-0001-2345-678X"
    assert normalize_orcid("not an orcid") is None


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code, self._p = status, payload

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), 0

    def get(self, *a, **k):
        self.calls += 1
        return self.responses.pop(0)


def test_retries_on_429_then_succeeds():
    s = FakeSession(FakeResponse(429), FakeResponse(503), FakeResponse(200, {"ok": 1}))
    assert HttpClient(session=s, backoff=0).get_json("http://x") == {"ok": 1}
    assert s.calls == 3


def test_gives_up_after_retries():
    s = FakeSession(*[FakeResponse(500)] * 3)
    with pytest.raises(RuntimeError):
        HttpClient(session=s, backoff=0).get_json("http://x")
    assert s.calls == 3


def test_404_returns_none_without_retry():
    s = FakeSession(FakeResponse(404))
    assert HttpClient(session=s).get_json("http://x") is None
    assert s.calls == 1


def test_client_error_is_raised_not_retried():
    s = FakeSession(FakeResponse(400))
    with pytest.raises(RuntimeError):
        HttpClient(session=s).get_json("http://x")
    assert s.calls == 1
