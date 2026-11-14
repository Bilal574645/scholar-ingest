# scholar-ingest

A small, tested pipeline that ingests an institution's publications from open scholarly sources
(**OpenAlex, Crossref, PubMed, ORCID**), merges them into one clean record per paper, flags data-quality
problems, and checks the result against what the institution actually publishes.

I built it to practise the workflow of an AI-assisted data-ingestion and testing role: let coding agents
write the routine code, then **verify their output** with golden data and tests that are proven to fail when the code breaks.

## What it does
| Step | Module | Notes |
|---|---|---|
| Fetch | `sources.py` | OpenAlex (cursor pagination by ROR id), Crossref (DOI enrichment), PubMed E-utilities, ORCID public API |
| Normalise | `models.py` | DOI / ORCID canonical forms, one common record shape |
| Merge | `merge.py` | De-duplicates across sources, unions authors, **flags conflicting values** (e.g. different years) instead of hiding them |
| Validate | `validate.py` | Missing title/year/authors, invalid DOI, implausible year, source conflicts; coverage vs. a reference DOI list |
| Store | `store.py` | JSON Lines (default), MongoDB, in-memory (tests); idempotent upserts |
| Report | `report.py` | Static HTML report |

## Run it
```bash
pip install -e ".[dev]"
# live ingestion (use your own e-mail in HttpClient user_agent for the "polite pool")
scholar-ingest ingest --ror https://ror.org/01jdpyv68 --pubmed-term "Saarland University[Affiliation]" --max-pages 2
# compare with a DOI list copied from the institution's own publication page
scholar-ingest check --reference data/reference_dois.txt
# or with MongoDB
docker compose up --build
```
Verify the ROR id of any institution at <https://ror.org> before using it.

## Testing approach
* **Unit tests** for every parser and normaliser, using realistic API payloads (`tests/fixtures.py`); no network needed.
* **Golden test** (`tests/golden/expected_merged.json`): the whole pipeline on fixed inputs must reproduce a hand-reviewed result.
* **Retry/pagination/idempotency tests** for the failure modes that bite in production (HTTP 429, repeated runs, cursor end).
* **Playwright end-to-end test** of the HTML report (including HTML-escaping of titles).
* **Mutation check** (`tools/mutation_check.py`): automatically introduces small bugs (`==`→`!=`, `<`→`<=`, `and`→`or`, ...)
  and confirms the test-suite fails for each one. A surviving mutant means a missing test.
  Current score: **~93%**. The remaining survivors are equivalent mutants (argparse `required=True`, JSON `ensure_ascii`).

Run everything: `pytest -q && python tools/mutation_check.py`

## Things I found while building it
* The first test run exposed that `http://dx.doi.org/...` was not normalised - a real bug, fixed.
* The first mutation run (74%) showed that the CLI, the Mongo store and the default year window were untested.

## Limitations / next steps
* ORCID and PubMed only match by DOI or title+year; fuzzy title matching would reduce duplicates.
* Crossref enrichment is sequential; batching with the `filter=doi:` endpoint would be faster.
