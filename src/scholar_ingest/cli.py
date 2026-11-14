"""Command line: `ingest` pulls data from the live APIs, `check` validates a stored dataset."""
import argparse
from pathlib import Path

from .http import HttpClient
from .pipeline import run_ingestion
from .report import render_html
from .store import JsonlStore, MongoStore
from .validate import check_quality, compare_to_reference
import os
import requests


def main(argv=None):
    p = argparse.ArgumentParser(prog="scholar-ingest")
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="ingest works for one institution")
    ing.add_argument("--ror", required=True,
                     help="ROR id URL, e.g. https://ror.org/01jdpyv68")
    ing.add_argument(
        "--pubmed-term", help="PubMed affiliation query, e.g. 'Saarland University[Affiliation]'")
    ing.add_argument("--orcid", action="append", default=[],
                     help="ORCID iD (repeatable)")
    ing.add_argument("--max-pages", type=int, default=1)
    ing.add_argument("--out", default="data/records.jsonl")
    ing.add_argument(
        "--mongo-uri", help="store in MongoDB instead of a JSONL file")

    chk = sub.add_parser(
        "check", help="validate stored records and write an HTML report")
    chk.add_argument("--records", default="data/records.jsonl")
    chk.add_argument("--reference", help="text file with one DOI per line")
    chk.add_argument("--report", default="data/report.html")

    a = p.parse_args(argv)
    if a.cmd == "ingest":
        store = MongoStore(a.mongo_uri) if a.mongo_uri else JsonlStore(a.out)
        try:
            recs = run_ingestion(HttpClient(), a.ror, store, a.max_pages, a.pubmed_term, a.orcid,
                                 openalex_key=os.environ.get("OPENALEX_API_KEY"))
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 401:
                raise SystemExit("OpenAlex needs a free API key: https://openalex.org/settings/api "
                                 "then set OPENALEX_API_KEY")
            raise
        print(f"Ingested {len(recs)} publications")
    else:
        recs = JsonlStore(a.records).all()
        issues = check_quality(recs)
        comparison = None
        if a.reference:
            comparison = compare_to_reference(
                recs, Path(a.reference).read_text().split())
            print(f"Coverage: {comparison['coverage']:.1%}, missing: {len(comparison['missing'])}, "
                  f"unexpected: {len(comparison['unexpected'])}")
        Path(a.report).parent.mkdir(parents=True, exist_ok=True)
        Path(a.report).write_text(render_html(
            recs, issues, comparison), encoding="utf-8")
        print(f"{len(recs)} records, {len(issues)} issues -> {a.report}")


if __name__ == "__main__":
    main()
