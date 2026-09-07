import os
import json
import re
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger("RAG")

HF_CACHE = os.path.expanduser(
    "~/.cache/huggingface/hub")
MODEL_DIR = os.path.join(
    HF_CACHE,
    "models--sentence-transformers--all-MiniLM-L6-v2",
    "snapshots", "c9745ed1d9f207416be6d2e6f8de32d1f16199bf")
MODEL_PATH = os.path.join(MODEL_DIR, "onnx", "model_quint8_avx2.onnx")

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..",
                        "opencode-project", "docs")
PROJECT_DIR = os.path.join(os.path.dirname(__file__), "..", "..",
                           "opencode-project")

INDEX_PATH = os.path.join(DOCS_DIR, ".rag_index.json")
VECTORS_PATH = os.path.join(DOCS_DIR, ".rag_vectors.npy")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 10

_session = None
_tokenizer = None

def _get_session():
    global _session
    if _session is None:
        import onnxruntime
        model_path = os.path.abspath(MODEL_PATH)
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"ONNX model not found at {model_path}")
        _session = onnxruntime.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"]
        )
    return _session

def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        from tokenizers import Tokenizer
        tok_path = os.path.join(MODEL_DIR, "tokenizer.json")
        _tokenizer = Tokenizer.from_file(tok_path)
    return _tokenizer

def _embed(texts: List[str]) -> np.ndarray:
    session = _get_session()
    tokenizer = _get_tokenizer()

    enc = tokenizer.encode_batch(texts, add_special_tokens=True)
    max_len = max(len(e.ids) for e in enc) if enc else 1
    max_len = min(max_len, 256)
    batch_size = len(texts)
    input_ids = np.zeros((batch_size, max_len), dtype=np.int64)
    attention_mask = np.zeros((batch_size, max_len), dtype=np.int64)
    token_type_ids = np.zeros((batch_size, max_len), dtype=np.int64)

    for i, e in enumerate(enc):
        ids = e.ids[:max_len]
        input_ids[i, :len(ids)] = ids
        attention_mask[i, :len(ids)] = 1

    ort_inputs = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "token_type_ids": token_type_ids
    }

    embeddings = session.run(None, ort_inputs)[0]
    mask = attention_mask[:, :, np.newaxis].astype(embeddings.dtype)
    pooled = np.sum(embeddings * mask, axis=1) / np.maximum(
        np.sum(mask, axis=1), 1e-9)
    return pooled / np.linalg.norm(pooled, axis=1, keepdims=True)

def _chunk_text(text: str, file_path: str) -> List[Dict]:
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) < CHUNK_SIZE:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "filePath": file_path
                })
            current_chunk = para + "\n\n"
    if current_chunk:
        chunks.append({
            "text": current_chunk.strip(),
            "filePath": file_path
        })
    return chunks

def _load_index():
    if not os.path.exists(INDEX_PATH):
        return {"documents": {}, "chunks": []}
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_index(index):
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

def _load_vectors():
    if not os.path.exists(VECTORS_PATH):
        return None
    return np.load(VECTORS_PATH).astype(np.float32)

def _save_vectors(vecs: np.ndarray):
    os.makedirs(os.path.dirname(VECTORS_PATH), exist_ok=True)
    np.save(VECTORS_PATH, vecs.astype(np.float32))

def ingest_file(file_path: str) -> Dict:
    abs_path = os.path.abspath(file_path)
    if not abs_path.startswith(os.path.abspath(DOCS_DIR)):
        base = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".."))
        proj = os.path.abspath(PROJECT_DIR)
        if not (abs_path.startswith(base) or abs_path.startswith(proj)):
            return {"error": f"Path not allowed: {file_path}"}

    if not os.path.isfile(abs_path):
        return {"error": f"File not found: {file_path}"}

    ext = os.path.splitext(abs_path)[1].lower()
    try:
        if ext == ".txt":
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        elif ext == ".md":
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        elif ext in (".py", ".js", ".ts", ".json", ".yaml", ".yml",
                     ".xml", ".html", ".css", ".sh", ".toml", ".ini",
                     ".cfg", ".conf", ".env", ".csv"):
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        elif ext == ".pdf":
            try:
                import PyPDF2
                text = ""
                with open(abs_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
            except ImportError:
                try:
                    import pdfminer.high_level as pm
                    text = pm.extract_text(abs_path)
                except ImportError:
                    return {"error": "No PDF parser available"}
        else:
            return {"error": f"Unsupported file type: {ext}"}
    except Exception as e:
        return {"error": str(e)}

    rel_path = os.path.relpath(abs_path, os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..",
                     "..", "opencode-project")))
    chunks = _chunk_text(text, rel_path)

    if not chunks:
        return {"error": "No content extracted"}

    index = _load_index()
    existing = index["documents"].get(rel_path, {})
    old_chunk_count = existing.get("chunk_count", 0)
    index["documents"][rel_path] = {
        "filePath": rel_path,
        "fileName": os.path.basename(rel_path),
        "fileSize": os.path.getsize(abs_path),
        "fileType": ext,
        "chunk_count": len(chunks)
    }

    old_chunks = index["chunks"]
    if old_chunk_count > 0:
        removed = 0
        new_chunks = []
        for c in old_chunks:
            if c["filePath"] == rel_path:
                removed += 1
            else:
                new_chunks.append(c)
        old_vectors = _load_vectors()
        index["chunks"] = new_chunks
        if old_vectors is not None and removed > 0:
            old_vectors = old_vectors[:len(new_chunks)]
            _save_vectors(old_vectors)

    old_len = len(index["chunks"])
    new_embeddings = _embed([c["text"] for c in chunks])

    for i, chunk in enumerate(chunks):
        chunk["chunkIndex"] = old_len + i
        index["chunks"].append(chunk)

    old_vecs = _load_vectors()
    if old_vecs is None:
        old_vecs = np.empty((0, new_embeddings.shape[1]),
                            dtype=np.float32)
    all_vecs = np.vstack([old_vecs, new_embeddings.astype(np.float32)])
    _save_vectors(all_vecs)
    _save_index(index)

    return {
        "status": "ok",
        "filePath": rel_path,
        "chunks": len(chunks),
        "total_chunks": len(index["chunks"])
    }

def query_documents(query: str, limit: int = TOP_K) -> Dict:
    index = _load_index()
    if not index["chunks"]:
        return {"results": [], "total_chunks": 0}

    vectors = _load_vectors()
    if vectors is None or len(vectors) != len(index["chunks"]):
        return {"error": "Vector index corrupted, re-ingest files",
                "results": []}

    query_vec = _embed([query])[0].astype(np.float32)
    from scipy.spatial.distance import cdist
    distances = cdist(
        query_vec.reshape(1, -1), vectors, metric="cosine"
    )[0]

    top_indices = np.argsort(distances)[:limit]
    results = []
    for idx in top_indices:
        chunk = index["chunks"][idx]
        dist = float(distances[idx])
        score = 1.0 - dist
        doc = index["documents"].get(chunk["filePath"], {})
        results.append({
            "filePath": chunk["filePath"],
            "chunkIndex": chunk.get("chunkIndex", idx),
            "text": chunk["text"][:500],
            "score": round(score, 4),
            "fileTitle": doc.get("fileName", chunk["filePath"])
        })

    return {
        "results": results,
        "total_chunks": len(index["chunks"]),
        "total_files": len(index["documents"])
    }

def list_files() -> List[Dict]:
    index = _load_index()
    files = []
    for fp, info in index["documents"].items():
        files.append(info)
    return files

def delete_file(file_path: str) -> Dict:
    abs_path = os.path.abspath(file_path)
    base = os.path.abspath(DOCS_DIR)
    if abs_path.startswith(base):
        rel_path = os.path.relpath(abs_path, base)
    elif abs_path.startswith(os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..",
                         "..", "opencode-project"))):
        rel_path = os.path.relpath(abs_path, os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..",
                         "..", "opencode-project")))
    else:
        return {"error": f"Path not allowed: {file_path}"}

    index = _load_index()
    if rel_path not in index["documents"]:
        return {"error": f"File not indexed: {rel_path}"}

    chunk_count = index["documents"][rel_path]["chunk_count"]
    del index["documents"][rel_path]

    old_len = len(index["chunks"])
    new_chunks = [c for c in index["chunks"]
                  if c["filePath"] != rel_path]
    index["chunks"] = new_chunks
    _save_index(index)

    old_vecs = _load_vectors()
    if old_vecs is not None:
        mask = np.ones(old_len, dtype=bool)
        removed = 0
        for i, c in enumerate(
                [c for c in index["chunks"]
                 if c["filePath"] == rel_path]):
            mask[i + removed] = False
            removed += 1
        new_vecs = old_vecs[mask]
        _save_vectors(new_vecs)

    return {"status": "ok", "filePath": rel_path, "removed": True}

def status() -> Dict:
    index = _load_index()
    return {
        "chunks": len(index["chunks"]),
        "files": len(index["documents"]),
        "docs_dir": DOCS_DIR
    }
