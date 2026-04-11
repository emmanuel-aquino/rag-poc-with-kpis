from rag import ask

print("Earnings Call Analyst — type 'quit' to exit\n")
print("Documents loaded. Ask me anything about the earnings calls.\n")

conversation_history = []

while True:
    question = input("You: ").strip()

    if question.lower() in ["quit", "exit", "q"]:
        print("Exiting.")
        break

    if not question:
        continue

    result = ask(question)

    print(f"\nAssistant: {result['answer']}")
    print(f"\n[Sources: {', '.join(result['source_docs'])} | "
          f"{result['retrieved_chunks']} chunks | "
          f"{result['latency_ms']}ms]\n")

    conversation_history.append({
        "question": question,
        "answer": result["answer"],
        "sources": result["source_docs"],
        "latency_ms": result["latency_ms"]
    })
