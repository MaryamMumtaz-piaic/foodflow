"""Lightweight JSON-file-backed repository pattern.

Every entity ("users", "restaurants", "menu_items", "orders", "reviews",
"coupons", "addresses", "deliveries", "categories") is stored as a JSON
array of dict records in app/data/<name>.json.

The `JsonStore` class exposes CRUD helpers with the same call signatures a
future PostgreSQL-backed repository would expose (list/get/create/update/
delete/query), so routes and services never touch raw file I/O and the
storage backend can later be swapped without changing call sites.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_locks: Dict[str, threading.Lock] = {}
_lock_guard = threading.Lock()


def _lock_for(name: str) -> threading.Lock:
    with _lock_guard:
        if name not in _locks:
            _locks[name] = threading.Lock()
        return _locks[name]


class JsonStore:
    """Generic repository for one JSON collection file."""

    def __init__(self, collection: str):
        self.collection = collection
        self.path = DATA_DIR / f"{collection}.json"
        self._lock = _lock_for(collection)
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._write([])

    # -- low level -------------------------------------------------
    def _read(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not self.path.exists():
                return []
            with open(self.path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)

    def _write(self, data: List[Dict[str, Any]]) -> None:
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    # -- CRUD --------------------------------------------------------
    def list_all(self) -> List[Dict[str, Any]]:
        return self._read()

    def get(self, id_: Any, id_field: str = "id") -> Optional[Dict[str, Any]]:
        for row in self._read():
            if str(row.get(id_field)) == str(id_):
                return row
        return None

    def find_one(self, predicate: Callable[[Dict[str, Any]], bool]) -> Optional[Dict[str, Any]]:
        for row in self._read():
            if predicate(row):
                return row
        return None

    def find_many(self, predicate: Callable[[Dict[str, Any]], bool]) -> List[Dict[str, Any]]:
        return [row for row in self._read() if predicate(row)]

    def create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        data = self._read()
        data.append(record)
        self._write(data)
        return record

    def update(self, id_: Any, patch: Dict[str, Any], id_field: str = "id") -> Optional[Dict[str, Any]]:
        data = self._read()
        updated = None
        for i, row in enumerate(data):
            if str(row.get(id_field)) == str(id_):
                row.update(patch)
                data[i] = row
                updated = row
                break
        if updated is not None:
            self._write(data)
        return updated

    def replace(self, id_: Any, record: Dict[str, Any], id_field: str = "id") -> Optional[Dict[str, Any]]:
        data = self._read()
        replaced = None
        for i, row in enumerate(data):
            if str(row.get(id_field)) == str(id_):
                data[i] = record
                replaced = record
                break
        if replaced is not None:
            self._write(data)
        return replaced

    def delete(self, id_: Any, id_field: str = "id") -> bool:
        data = self._read()
        new_data = [row for row in data if str(row.get(id_field)) != str(id_)]
        deleted = len(new_data) != len(data)
        if deleted:
            self._write(new_data)
        return deleted

    def next_id(self, prefix: str = "") -> str:
        data = self._read()
        max_num = 0
        for row in data:
            raw = str(row.get("id", ""))
            digits = "".join(ch for ch in raw if ch.isdigit())
            if digits:
                max_num = max(max_num, int(digits))
        return f"{prefix}{max_num + 1}"

    def replace_all(self, data: List[Dict[str, Any]]) -> None:
        self._write(data)


# Singletons for each collection used across the app
users_store = JsonStore("users")
addresses_store = JsonStore("addresses")
restaurants_store = JsonStore("restaurants")
categories_store = JsonStore("categories")
menu_items_store = JsonStore("menu_items")
orders_store = JsonStore("orders")
reviews_store = JsonStore("reviews")
coupons_store = JsonStore("coupons")
deliveries_store = JsonStore("deliveries")
carts_store = JsonStore("carts")
tokens_store = JsonStore("tokens")
complaints_store = JsonStore("complaints")
