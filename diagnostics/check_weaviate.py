from src.vector_store import connect_weaviate

client = connect_weaviate()

try:
    collection = client.collections.get("HRPolicy")
    config = collection.config.get()

    print("Collection:", config.name)
    print("Vector configuration:", config.vector_config)
    print("Object count:", collection.aggregate.over_all(total_count=True).total_count)

finally:
    client.close()