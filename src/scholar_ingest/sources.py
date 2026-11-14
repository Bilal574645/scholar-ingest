"""Clients + parsers for OpenAlex, Crossref, PubMed (NCBI E-utilities) and ORCID."""
from .models import make_record, normalize_orcid

OPENALEX = "https://api.openalex.org/works"
CROSSREF = "https://api.crossref.org/works/"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
ORCID = "https://pub.orcid.org/v3.0/"


# ---------- OpenAlex ----------
def parse_openalex_work(work):
    authors = []
    for a in work.get("authorships", []):
        author = a.get("author") or {}
        if author.get("display_name"):
            authors.append(
                {"name": author["display_name"], "orcid": normalize_orcid(author.get("orcid"))})
    return make_record(work.get("doi"), work.get("title"), work.get("publication_year"), authors, "openalex")


def fetch_openalex(client, ror, max_pages=1, per_page=200, api_key=None):
    """Cursor-paginate through all works of an institution (identified by ROR id)."""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    cursor, records = "*", []
    for _ in range(max_pages):
        data = client.get_json(OPENALEX, params={
            "filter": f"institutions.ror:{ror}", "per-page": per_page, "cursor": cursor},
            headers=headers)
        if not data:
            break
        records.extend(parse_openalex_work(w) for w in data.get("results", []))
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
    return records

# ---------- Crossref ----------


def parse_crossref(message):
    authors = []
    for a in message.get("author", []):
        name = " ".join(p for p in (a.get("given"), a.get("family")) if p)
        if name:
            authors.append(
                {"name": name, "orcid": normalize_orcid(a.get("ORCID"))})
    title = (message.get("title") or [None])[0]
    parts = ((message.get("issued") or {}).get("date-parts") or [[None]])[0]
    return make_record(message.get("DOI"), title, parts[0] if parts else None, authors, "crossref")


def fetch_crossref(client, doi):
    data = client.get_json(CROSSREF + doi)
    return parse_crossref(data["message"]) if data else None


# ---------- PubMed ----------
def parse_pubmed(doc):
    doi = next((i["value"] for i in doc.get("articleids", [])
               if i.get("idtype") == "doi"), None)
    year = (doc.get("pubdate") or "")[:4]
    authors = [{"name": a["name"], "orcid": None}
               for a in doc.get("authors", []) if a.get("name")]
    return make_record(doi, doc.get("title"), year if year.isdigit() else None, authors, "pubmed")


def fetch_pubmed(client, term, retmax=100):
    search = client.get_json(EUTILS + "esearch.fcgi",
                             params={"db": "pubmed", "term": term, "retmax": retmax, "retmode": "json"})
    ids = ((search or {}).get("esearchresult") or {}).get("idlist", [])
    if not ids:
        return []
    summary = client.get_json(EUTILS + "esummary.fcgi",
                              params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
    result = (summary or {}).get("result", {})
    return [parse_pubmed(result[uid]) for uid in ids if uid in result]


# ---------- ORCID ----------
def parse_orcid_works(data, orcid):
    records = []
    for group in (data or {}).get("group", []):
        summary = group["work-summary"][0]
        doi = next((e["external-id-value"] for e in (summary.get("external-ids") or {}).get("external-id", [])
                    if e.get("external-id-type") == "doi"), None)
        title = ((summary.get("title") or {}).get("title") or {}).get("value")
        year = (((summary.get("publication-date") or {}).get("year"))
                or {}).get("value")
        records.append(make_record(doi, title, year, [
                       {"name": None, "orcid": orcid}], "orcid"))
    return records


def fetch_orcid(client, orcid):
    data = client.get_json(f"{ORCID}{orcid}/works")
    return parse_orcid_works(data, orcid)
