"""Firebase download and processing utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from kg_llm_new.logging_utils import get_logger

LOGGER = get_logger(__name__)

try:  # Optional dependency guard
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:  # pragma: no cover - handled at runtime
    firebase_admin = None
    credentials = None
    firestore = None


@dataclass
class FirebaseFilter:
    """Filter applied to a Firestore collection."""

    field_path: str
    operator: str
    value: Any


@dataclass
class FirebaseDownloadConfig:
    """Configuration for downloading Firestore documents."""

    credentials_path: Path
    project_id: Optional[str] = None
    collection: str = ""
    filters: Sequence[FirebaseFilter] = ()
    limit: Optional[int] = None
    select_fields: Sequence[str] = ()


class FirebaseDownloader:
    """Download documents from Firebase Firestore with filter support."""

    def __init__(self, config: FirebaseDownloadConfig) -> None:
        if firebase_admin is None or credentials is None or firestore is None:
            raise RuntimeError(
                "firebase-admin is required. Install with `pip install firebase-admin`."
            )
        self.config = config
        cred = credentials.Certificate(str(config.credentials_path))
        options = {"projectId": config.project_id} if config.project_id else None
        if not firebase_admin._apps:  # type: ignore[attr-defined]
            firebase_admin.initialize_app(cred, options)
        self.client = firestore.client()

    def download(self) -> List[Dict[str, Any]]:
        """Download documents from Firestore according to config."""

        query = self.client.collection(self.config.collection)
        for flt in self.config.filters:
            query = query.where(flt.field_path, flt.operator, flt.value)
        if self.config.select_fields:
            query = query.select(list(self.config.select_fields))
        if self.config.limit:
            query = query.limit(self.config.limit)

        documents = list(query.stream())
        LOGGER.info(
            "Fetched %d documents from collection '%s'",
            len(documents),
            self.config.collection,
        )
        return [doc.to_dict() | {"_doc_id": doc.id} for doc in documents]


class FirebaseProcessor:
    """Convert Firestore documents into shard JSONL dumps."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_documents(self, documents: Iterable[Dict[str, Any]], filename: str) -> Path:
        docs_list = documents if isinstance(documents, list) else list(documents)
        path = self.output_dir / filename
        with path.open("w", encoding="utf-8") as handle:
            for doc in docs_list:
                handle.write(json.dumps(doc, ensure_ascii=False) + "\n")
        LOGGER.info("Wrote %d documents to %s", len(docs_list), path)
        return path

    def dump_raw(self, documents: Iterable[Dict[str, Any]]) -> Path:
        """Write raw documents to `firebase_raw.jsonl`."""

        return self.write_documents(documents, "firebase_raw.jsonl")

    def process_to_shards(self, documents: Iterable[Dict[str, Any]]) -> Dict[str, Path]:
        """Split documents into shard JSONL files.

        Each document is expected to declare a `shard_type` key with value
        among {"one_hop", "two_hop", "literal", "description"}. The
        `payload` key should contain the canonical triple/path structure for
        that shard.
        """

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for doc in documents:
            shard_type = str(doc.get("shard_type", "")).strip()
            if not shard_type:
                LOGGER.warning("Skipping document without shard_type: %s", doc)
                continue
            payload = doc.get("payload") or {}
            if not payload:
                LOGGER.warning("Skipping document without payload: %s", doc)
                continue
            grouped.setdefault(shard_type, []).append(payload)

        output_paths: Dict[str, Path] = {}
        for shard_type, items in grouped.items():
            filename = f"{shard_type}.jsonl"
            path = self.output_dir / filename
            with path.open("w", encoding="utf-8") as handle:
                for item in items:
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            LOGGER.info("Wrote %d entries to %s", len(items), path)
            output_paths[shard_type] = path
        return output_paths