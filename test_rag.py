from rag import ask
import json

test_questions = [
    "What was the revenue guidance for next quarter?",
    "What risk factors did management highlight?",
    "How did gross margin compare to the same period last year?",
    "What did the CEO say about headcount or hiring plans?",
    "Were there any mentions of macroeconomic concerns?",
    "What were the main drivers of revenue growth?",
    "Did management mention any new product launches?",
    "What was said about operating expenses?",
    "How did actual results compare to analyst expectations?",
    "What questions did analysts ask during the Q&A section?"
]

for q in test_questions:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    result = ask(q)
    print(f"A: {result['answer']}")
    print(f"\nSources: {', '.join(result['source_docs'])}")
    print(f"Chunks used: {result['retrieved_chunks']} | Latency: {result['latency_ms']}ms")
