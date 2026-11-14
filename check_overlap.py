import json
recs = [json.loads(l) for l in open("data/records.jsonl", encoding="utf-8")]
pm = [r for r in recs if r["sources"] == ["pubmed"]]
oa = {r["doi"] for r in recs if r["doi"] and "openalex" in r["sources"]}
print("pubmed-only:", len(pm), "| with DOI:", sum(1 for r in pm if r["doi"]))
print("pubmed DOIs also in openalex set:",
      sum(1 for r in pm if r["doi"] in oa))
for r in pm[:3]:
    print(r["doi"], "|", r["year"], "|", r["title"])
