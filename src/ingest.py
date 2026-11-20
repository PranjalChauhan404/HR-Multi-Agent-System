from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICIES_DIR = PROJECT_ROOT / "data" / "policies"


def load_policy_documents():
    """Load all Markdown policy documents."""
    documents = []

    for file_path in sorted(POLICIES_DIR.glob("*.md")):
        content = file_path.read_text(encoding="utf-8").strip()

        if content:
            documents.append({
                "source": file_path.name,
                "content": content
            })

    return documents


def chunk_text(text, chunk_size=800, overlap=100):
    """Split text into overlapping chunks."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Invalid chunk_size or overlap.")

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def load_policy_chunks():
    """Load policies and convert them into searchable chunks."""
    documents = load_policy_documents()
    all_chunks = []

    for document in documents:
        chunks = chunk_text(document["content"])

        for index, chunk in enumerate(chunks):
            all_chunks.append({
                "source": document["source"],
                "chunk_index": index,
                "text": chunk
            })

    return all_chunks


if __name__ == "__main__":
    documents = load_policy_documents()
    chunks = load_policy_chunks()

    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")

    for chunk in chunks:
        print(f"\nSource: {chunk['source']}")
        print(f"Chunk: {chunk['chunk_index']}")
        print(f"Text: {chunk['text'][:100]}...")