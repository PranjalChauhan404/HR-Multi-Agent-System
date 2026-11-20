from src.vector_store import connect_weaviate

client = connect_weaviate()

try:
    collection = client.collections.get("HRPolicy")

    print("Collection count:",
          collection.aggregate.over_all(total_count=True).total_count)

    print("\nTesting query without vectors...")

    result = collection.query.fetch_objects(limit=8)

    print("Objects returned:", len(result.objects))

    for obj in result.objects:
        print(
            obj.properties.get("source"),
            "|",
            obj.properties.get("chunk_index"),
        )

    print("\nTesting vector search...")

    from src.rag import embedding_model

    vector = embedding_model.encode(
        "What is the work-from-home policy?"
    ).tolist()

    result = collection.query.near_vector(
        near_vector=vector,
        limit=8,
        return_metadata=["distance"],
    )

    print("Vector results returned:", len(result.objects))

    for obj in result.objects:
        print(
            obj.properties.get("source"),
            "|",
            obj.properties.get("chunk_index"),
            "| distance:",
            obj.metadata.distance,
        )

finally:
    client.close()