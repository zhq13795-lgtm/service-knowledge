"""Local document storage and evidence retrieval."""

import math
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


def tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    for segment in re.findall(r"[\u4e00-\u9fff]+", text):
        words.extend(segment[i:i + 2] for i in range(len(segment) - 1))
        if len(segment) == 1:
            words.append(segment)
    return words


def split_text(text: str, size: int = 450) -> list[str]:
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - 60
    return chunks


class KnowledgeStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
                    position INTEGER NOT NULL, content TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def documents(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("""
                SELECT d.id, d.name, d.created_at, COUNT(c.id) AS chunk_count
                FROM documents d LEFT JOIN chunks c ON c.document_id = d.id
                GROUP BY d.id ORDER BY d.created_at DESC, d.rowid DESC
            """).fetchall()
        return [dict(row) for row in rows]

    def add(self, name: str, text: str) -> dict:
        chunks = split_text(text)
        if not chunks:
            raise ValueError("文档内容不能为空")
        document_id = uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO documents (id, name) VALUES (?, ?)", (document_id, name))
            db.executemany(
                "INSERT INTO chunks (id, document_id, position, content) VALUES (?, ?, ?, ?)",
                [(f"{document_id}:{i + 1}", document_id, i + 1, chunk) for i, chunk in enumerate(chunks)],
            )
        return {"id": document_id, "name": name, "chunk_count": len(chunks)}

    def search(self, question: str, limit: int = 3) -> list[dict]:
        query = set(tokens(question))
        if not query:
            return []
        with self.connect() as db:
            rows = db.execute("""
                SELECT c.id AS citation_id, d.name AS source, c.position, c.content
                FROM chunks c JOIN documents d ON d.id = c.document_id
            """).fetchall()
        if not rows:
            return []
        counts = [Counter(tokens(row["content"])) for row in rows]
        average = sum(sum(count.values()) for count in counts) / len(counts) or 1
        frequencies = {term: sum(term in count for count in counts) for term in query}
        ranked = []
        for row, count in zip(rows, counts):
            length = sum(count.values())
            score = 0.0
            for term in query:
                frequency = count[term]
                if not frequency:
                    continue
                idf = math.log(1 + (len(rows) - frequencies[term] + .5) / (frequencies[term] + .5))
                score += idf * frequency * 2.2 / (frequency + 1.2 * (.25 + .75 * length / average))
            if score > 0:
                ranked.append({**dict(row), "score": round(score, 4)})
        return sorted(ranked, key=lambda item: item["score"], reverse=True)[:limit]


def answer(question: str, sources: list[dict]) -> str:
    if not sources:
        return "当前知识库没有找到足够的相关资料，请补充问题描述或导入对应文档。"
    query = set(tokens(question))
    lines = []
    for index, source in enumerate(sources, 1):
        sentences = [part.strip(" #\n") for part in re.split(r"[。！？\n]+", source["content"]) if part.strip(" #\n")]
        relevant = sorted(sentences, key=lambda part: len(query & set(tokens(part))), reverse=True)
        excerpts = [part for part in relevant if query & set(tokens(part))][:2]
        if excerpts:
            lines.append(f"{'；'.join(excerpts)}。[{index}]")
    return "根据已导入资料：\n\n" + "\n\n".join(lines)
