from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.knowledge import KnowledgeStore, answer


ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Service Knowledge", version="0.1.0")


def get_store() -> KnowledgeStore:
    return KnowledgeStore(ROOT / ".local" / "knowledge.db")


def seed_samples(store: KnowledgeStore):
    if not store.documents():
        for path in sorted((ROOT / "samples").glob("*.md")):
            store.add(path.name, path.read_text(encoding="utf-8"))


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/documents")
def documents():
    store = get_store()
    seed_samples(store)
    return {"documents": store.documents()}


@app.post("/api/documents")
async def upload(file: UploadFile = File(...)):
    name = (file.filename or "").replace("\\", "/").split("/")[-1]
    if Path(name).suffix.lower() not in {".md", ".txt"}:
        raise HTTPException(422, "目前支持 UTF-8 编码的 .md 和 .txt 文档")
    content = await file.read(1024 * 1024 + 1)
    if len(content) > 1024 * 1024:
        raise HTTPException(413, "单个文档不能超过 1 MB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "请将文档保存为 UTF-8 编码后重新上传") from exc
    if not text.strip():
        raise HTTPException(422, "文档内容不能为空")
    store = get_store()
    seed_samples(store)
    return store.add(name, text)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.post("/api/query")
def query(request: Question):
    question = request.question.strip()
    if not question:
        raise HTTPException(422, "请输入问题")
    store = get_store()
    seed_samples(store)
    sources = store.search(question)
    return {"answer": answer(question, sources), "sources": sources}
