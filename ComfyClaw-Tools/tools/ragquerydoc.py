from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path


SETTINGS_FILE = Path(__file__).resolve().parent.parent / "ragquerydoc_settings.txt"
CACHE_DIR = Path(__file__).resolve().parent.parent / "ragquerydoc_cache"
BUNDLE_FILE = CACHE_DIR / "embedded_bundle.json"
CURRENT_PATH_FILE = CACHE_DIR / "current_path.json"
OLLAMA_URL = "http://127.0.0.1:11434/api/embed"
EMBED_BATCH_SIZE = 32


ACTION_ARGUMENTS = {
    "query": {"path", "query", "chunk-type", "chunk-size", "out"},
    "path": {"path", "query", "chunk-type", "chunk-size", "out"},
}


def parse_command(args: list[str]):
    if not args:
        return None, None, "Error: missing action"

    action = args[0]
    parsed_args: dict[str, str] = {}
    raw_args = args[1:]
    index = 0

    while index < len(raw_args):
        key = raw_args[index]
        if not key.startswith("--"):
            return None, None, f"Error: invalid argument {key}"
        if index + 1 >= len(raw_args):
            return None, None, f"Error: missing value for {key}"

        parsed_args[key[2:]] = raw_args[index + 1]
        index += 2

    return action, parsed_args, None


def validate_args(parsed_args: dict[str, str], allowed: set[str], required: set[str]):
    for key in parsed_args:
        if key not in allowed:
            return f"Error: unknown argument --{key}"

    for key in required:
        if key not in parsed_args:
            return f"Error: missing required argument --{key}"

    return None


def resolve_input_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (Path.cwd() / path).resolve()

    resolved.relative_to(Path.cwd().resolve())
    return resolved


def resolve_output_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (Path.cwd() / path).resolve()

    resolved.relative_to(Path.cwd().resolve())
    return resolved


def save_text(text: str, output_value: str) -> str:
    output_path = resolve_output_path(output_value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return f"Saved to {output_path}"


def load_settings() -> dict[str, str]:
    if not SETTINGS_FILE.is_file():
        raise FileNotFoundError(f"Settings file not found: {SETTINGS_FILE}")

    settings: dict[str, str] = {}
    for raw_line in SETTINGS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid settings line: {raw_line}")

        key, value = line.split("=", 1)
        settings[key.strip()] = value.strip()

    for required_key in {"overlap", "before", "after", "topk_results", "embedding_model"}:
        if required_key not in settings:
            raise ValueError(f"Missing settings key: {required_key}")

    return settings


def read_document_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        import fitz

        document = fitz.open(path)
        parts: list[str] = []
        for page in document:
            parts.append(page.get_text("text"))
        return "\n".join(parts)

    text = path.read_text(encoding="utf-8", errors="ignore")

    if suffix in {".html", ".htm"}:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return "\n".join(part.strip() for part in soup.stripped_strings if part.strip())

    return text


def split_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    return [part.strip() for part in re.split(r"\n\s*\n+", normalized) if part.strip()]


def split_words(text: str) -> list[str]:
    return text.split()


def chunk_paragraphs(paragraphs: list[str], chunk_size: int, overlap: int):
    chunks: list[dict[str, object]] = []
    step = chunk_size - overlap

    for start in range(0, len(paragraphs), step):
        end = min(len(paragraphs), start + chunk_size)
        window = paragraphs[start:end]
        if not window:
            continue

        chunks.append(
            {
                "index": len(chunks),
                "start_unit": start,
                "end_unit": end - 1,
                "text": "\n\n".join(window),
            }
        )

        if end >= len(paragraphs):
            break

    return chunks


def chunk_words(words: list[str], chunk_size: int, overlap: int):
    chunks: list[dict[str, object]] = []
    step = chunk_size - overlap

    for start in range(0, len(words), step):
        end = min(len(words), start + chunk_size)
        window = words[start:end]
        if not window:
            continue

        chunks.append(
            {
                "index": len(chunks),
                "start_unit": start,
                "end_unit": end - 1,
                "text": " ".join(window),
            }
        )

        if end >= len(words):
            break

    return chunks


def chunk_text(text: str, chunk_type: str, chunk_size: int, overlap: int):
    if chunk_type in {"paragraph", "paragraphs"}:
        paragraphs = split_paragraphs(text)
        if not paragraphs:
            return []
        return chunk_paragraphs(paragraphs, chunk_size, overlap)

    if chunk_type in {"word", "words"}:
        words = split_words(text)
        if not words:
            return []
        return chunk_words(words, chunk_size, overlap)

    raise ValueError(f"Unsupported chunk type: {chunk_type}")


def normalize_vector(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector
    return [value / magnitude for value in vector]


def dot_product(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def embed_inputs(model: str, inputs: list[str]) -> list[list[float]]:
    import requests

    all_embeddings: list[list[float]] = []
    for start in range(0, len(inputs), EMBED_BATCH_SIZE):
        batch = inputs[start : start + EMBED_BATCH_SIZE]
        response = requests.post(
            OLLAMA_URL,
            json={"model": model, "input": batch},
            timeout=180,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise ValueError("Invalid embedding response")
        all_embeddings.extend(embeddings)

    return all_embeddings


def ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def document_signature(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def build_fingerprint(path: Path, chunk_type: str, chunk_size: int, settings: dict[str, str]) -> dict[str, object]:
    return {
        "document": document_signature(path),
        "chunk_type": chunk_type,
        "chunk_size": chunk_size,
        "overlap": int(settings["overlap"]),
        "before": int(settings["before"]),
        "after": int(settings["after"]),
        "embedding_model": settings["embedding_model"],
    }


def parse_non_negative_int(value: str, name: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if number < 0:
        raise ValueError(f"{name} must be 0 or greater")

    return number


def parse_positive_int(value: str, name: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if number <= 0:
        raise ValueError(f"{name} must be greater than 0")

    return number


def load_json(path: Path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def cache_matches(fingerprint: dict[str, object]) -> bool:
    current = load_json(CURRENT_PATH_FILE)
    bundle = load_json(BUNDLE_FILE)
    if not isinstance(current, dict) or not isinstance(bundle, dict):
        return False
    return current == fingerprint and bundle.get("fingerprint") == fingerprint


def build_bundle(path: Path, chunk_type: str, chunk_size: int, settings: dict[str, str]) -> dict[str, object]:
    text = read_document_text(path)
    overlap = parse_non_negative_int(settings["overlap"], "overlap")

    if chunk_size <= 0:
        raise ValueError("chunk size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap must be 0 or greater")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk size")

    chunks = chunk_text(text, chunk_type, chunk_size, overlap)
    if not chunks:
        raise ValueError("document produced no chunks")

    model = settings["embedding_model"]
    chunk_texts = [str(chunk["text"]) for chunk in chunks]
    raw_embeddings = embed_inputs(model, chunk_texts)

    if len(raw_embeddings) != len(chunks):
        raise ValueError("embedding count did not match chunk count")

    for chunk, embedding in zip(chunks, raw_embeddings):
        chunk["embedding"] = normalize_vector(embedding)
        chunk["text_hash"] = hashlib.sha256(str(chunk["text"]).encode("utf-8")).hexdigest()

    fingerprint = build_fingerprint(path, chunk_type, chunk_size, settings)

    bundle = {
        "fingerprint": fingerprint,
        "chunks": chunks,
    }

    ensure_cache_dir()
    BUNDLE_FILE.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    CURRENT_PATH_FILE.write_text(json.dumps(fingerprint, ensure_ascii=False), encoding="utf-8")

    return bundle


def load_or_build_bundle(path: Path, chunk_type: str, chunk_size: int, settings: dict[str, str]):
    fingerprint = build_fingerprint(path, chunk_type, chunk_size, settings)
    if cache_matches(fingerprint):
        bundle = load_json(BUNDLE_FILE)
        if isinstance(bundle, dict):
            return bundle, "reused"

    return build_bundle(path, chunk_type, chunk_size, settings), "rebuilt"


def query_bundle(bundle: dict[str, object], query: str, settings: dict[str, str]) -> str:
    chunks = bundle.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("embedded bundle is empty")

    query_embedding = embed_inputs(settings["embedding_model"], [query])[0]
    normalized_query = normalize_vector(query_embedding)

    scored_chunks: list[tuple[float, dict[str, object]]] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        embedding = chunk.get("embedding")
        if not isinstance(embedding, list):
            continue
        score = dot_product(normalized_query, embedding)
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    before = parse_non_negative_int(settings["before"], "before")
    after = parse_non_negative_int(settings["after"], "after")
    topk_results = parse_positive_int(settings["topk_results"], "topk_results")
    lines: list[str] = []

    for rank, (score, chunk) in enumerate(scored_chunks[:topk_results], start=1):
        chunk_index = int(chunk["index"])
        start_index = max(0, chunk_index - before)
        end_index = min(len(chunks) - 1, chunk_index + after)
        context_texts = [str(chunks[index]["text"]) for index in range(start_index, end_index + 1)]

        lines.append(f"MATCH {rank}")
        lines.append(f"SCORE: {score:.6f}")
        lines.append(f"CHUNK INDEX: {chunk_index}")
        lines.append(f"CONTEXT CHUNKS: {start_index}-{end_index}")
        lines.append("TEXT:")
        lines.append("\n\n".join(context_texts).strip())
        lines.append("")

    return "\n".join(lines).rstrip()


def run(args: list[str]) -> str:
    action, parsed_args, error = parse_command(args)
    if error:
        return error

    if action not in {"query", "path"}:
        return f"Error: unknown action {action}"

    error = validate_args(
        parsed_args,
        {"path", "query", "chunk-type", "chunk-size", "out"},
        {"path", "query", "chunk-type", "chunk-size"},
    )
    if error:
        return error

    try:
        chunk_size = int(parsed_args["chunk-size"])
    except ValueError:
        return "Error: chunk size must be an integer"

    chunk_type = parsed_args["chunk-type"].strip().lower()

    try:
        settings = load_settings()
        document_path = resolve_input_path(parsed_args["path"])
        bundle, cache_state = load_or_build_bundle(document_path, chunk_type, chunk_size, settings)
        result = query_bundle(bundle, parsed_args["query"], settings)
        total_chunks = len(bundle.get("chunks", []))

        header = [
            f"CACHE: {cache_state}",
            f"DOCUMENT: {document_path}",
            f"CHUNK TYPE: {chunk_type}",
            f"CHUNK SIZE: {chunk_size}",
            f"TOTAL CHUNKS: {total_chunks}",
            f"OVERLAP: {settings['overlap']}",
            f"TOPK RESULTS: {settings['topk_results']}",
            f"MODEL: {settings['embedding_model']}",
            "",
        ]
        final_text = "\n".join(header) + result

        if "out" in parsed_args:
            return save_text(final_text, parsed_args["out"])

        return final_text
    except Exception as exc:
        return f"Error: {exc}"
