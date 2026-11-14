"""Storage back-ends: in-memory (tests), JSON Lines (default), MongoDB (docker-compose)."""
import json
from pathlib import Path

from .models import record_key


class MemoryStore:
    def __init__(self):
        self.data = {}

    def upsert_many(self, records):
        for r in records:
            self.data[record_key(r)] = r

    def all(self):
        return list(self.data.values())


class JsonlStore:
    def __init__(self, path):
        self.path = Path(path)

    def upsert_many(self, records):
        existing = {record_key(r): r for r in self.all()}
        existing.update({record_key(r): r for r in records})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for r in existing.values():
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def all(self):
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]


class MongoStore:
    def __init__(self, uri="mongodb://localhost:27017", db="scholar", collection="publications"):
        from pymongo import MongoClient
        self.col = MongoClient(uri)[db][collection]

    def upsert_many(self, records):
        for r in records:
            self.col.replace_one({"_id": record_key(r)}, {"_id": record_key(r), **r}, upsert=True)

    def all(self):
        return [{k: v for k, v in d.items() if k != "_id"} for d in self.col.find()]
