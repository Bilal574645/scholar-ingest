"""Static HTML report so results can be inspected (and tested end-to-end with Playwright)."""
import html


def render_html(records, issues, comparison=None):
    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(r.get("doi") or "-"), html.escape(r.get("title") or "-"),
            r.get("year") or "-", html.escape(", ".join(r["sources"])))
        for r in records)
    issue_items = "".join(
        f"<li class='issue'>{html.escape(str(i['id']))}: {html.escape(i['issue'])}</li>" for i in issues)
    cov = ""
    if comparison:
        cov = f"<p id='coverage'>Coverage vs reference: {comparison['coverage']:.1%}</p>"
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Ingestion report</title></head><body>"
        f"<h1>Ingestion report</h1><p id='count'>{len(records)} publications</p>{cov}"
        "<table id='records'><thead><tr><th>DOI</th><th>Title</th><th>Year</th><th>Sources</th></tr></thead>"
        f"<tbody>{rows}</tbody></table><h2>Data-quality issues</h2><ul id='issues'>{issue_items}</ul></body></html>"
    )
