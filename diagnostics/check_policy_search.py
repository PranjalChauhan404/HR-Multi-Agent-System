from src.rag import retrieve_context

questions = [
    "What is the work-from-home policy?",
    "What expenses are eligible for reimbursement?",
    "How many sick leave days do employees receive?",
    "What is the company code of conduct?",
]

for question in questions:
    print("\nQUESTION:", question)

    for result in retrieve_context(question):
        print(
            "SOURCE:", result["source"],
            "| DISTANCE:", round(result["distance"], 4),
        )
        print("TEXT:", result["text"][:150])