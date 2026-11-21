import time
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from sentence_transformers import SentenceTransformer

from src.ingest import load_policy_chunks


COLLECTION_NAME = "HRPolicy"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def connect_weaviate():
    """Connect to the local Weaviate instance."""
    client = weaviate.connect_to_local(
        host="localhost",
        port=18080,
        grpc_port=50052,
    )

    if not client.is_ready():
        client.close()
        raise RuntimeError("Weaviate is not ready.")

    return client


def create_policy_collection(client):
    """Create the HR policy collection if it doesn't exist."""
    if client.collections.exists(COLLECTION_NAME):
        return client.collections.get(COLLECTION_NAME)

    return client.collections.create(
        name=COLLECTION_NAME,
        vector_config=Configure.Vectors.self_provided(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="source", data_type=DataType.TEXT),
            Property(name="chunk_index", data_type=DataType.INT),
        ],
    )


def index_policy_chunks(collection, model):
    """Embed policy chunks and store them in Weaviate."""
    chunks = load_policy_chunks()

    if not chunks:
        raise ValueError("No policy chunks found in data/policies/.")

    # Clear existing policy records before re-indexing.
    for item in collection.iterator(include_vector=False):
        collection.data.delete_by_id(item.uuid)

    indexed_count = 0

    with collection.batch.dynamic() as batch:
        for chunk in chunks:
            vector = model.encode(chunk["text"]).tolist()

            batch.add_object(
                properties={
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "chunk_index": chunk["chunk_index"],
                },
                vector=vector,
            )

    failed_objects = collection.batch.failed_objects

    if failed_objects:
        raise RuntimeError(
            f"Failed to index {len(failed_objects)} policy chunks. "
            f"First error: {failed_objects[0]}"
        )

    indexed_count = collection.aggregate.over_all(total_count=True).total_count

    print(f"Successfully indexed {indexed_count} policy chunks.")

def search_policies(collection, model, question, limit=3):
    """Retrieve relevant HR policy chunks using cosine similarity."""
    import numpy as np

    overall_start = time.perf_counter()

    # 1. Embedding generation
    embedding_start = time.perf_counter()

    query_vector = np.asarray(
        model.encode(question),
        dtype=np.float32,
    )

    print(
        f"[TIMING] Query embedding: "
        f"{time.perf_counter() - embedding_start:.2f}s"
    )

    query_norm = np.linalg.norm(query_vector)

    if query_norm == 0:
        return []

    # 2. Fetching vectors and calculating similarity
    search_start = time.perf_counter()

    matches = []

    for item in collection.iterator(include_vector=True):
        vector = item.vector

        if isinstance(vector, dict):
            vector = vector.get("default") or next(
                iter(vector.values()), None
            )

        if vector is None:
            continue

        document_vector = np.asarray(vector, dtype=np.float32)
        document_norm = np.linalg.norm(document_vector)

        if document_norm == 0:
            continue

        similarity = np.dot(
            query_vector, document_vector
        ) / (query_norm * document_norm)

        distance = float(1.0 - similarity)

        matches.append({
            "text": item.properties["text"],
            "source": item.properties["source"],
            "chunk_index": item.properties["chunk_index"],
            "distance": distance,
        })

    matches.sort(key=lambda result: result["distance"])

    print(
        f"[TIMING] Weaviate iteration + similarity: "
        f"{time.perf_counter() - search_start:.2f}s"
    )

    print(
        f"[TIMING] Total vector search: "
        f"{time.perf_counter() - overall_start:.2f}s"
    )

    return matches[:limit]

if __name__ == "__main__":
    client = connect_weaviate()

    try:
        collection = create_policy_collection(client)

        print("Connected to Weaviate successfully.")
        print("Loading embedding model...")

        model = SentenceTransformer(EMBEDDING_MODEL)

        print("Indexing HR policies...")
        index_policy_chunks(collection, model)

        question = "How many sick leave days do employees receive?"

        print(f"\nQuestion: {question}")
        print("\nRetrieved policy sections:")

        results = search_policies(collection, model, question)

        for result in results:
            print(f"\nSource: {result['source']}")
            print(f"Chunk: {result['chunk_index']}")
            print(f"Distance: {result['distance']}")
            print(f"Text: {result['text']}")

    finally:
        client.close()