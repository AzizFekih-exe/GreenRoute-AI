from src.ai_agents.gatekeeper import gatekeeper
from src.ai_agents.librarian import librarian
from src.ai_agents.researcher import researcher
from src.ai_agents.constructor import constructor

def run_pipeline(question: str) -> str:
    print(f"\n{'='*60}")
    print(f"❓ QUESTION: {question}")
    print(f"{'='*60}")

    # Step 1: Gatekeeper
    gate = gatekeeper(question)
    if not gate.get("allowed", True):
        return (
            f"🚫 **[GATEKEEPER BLOCKED]**\n\n"
            f"Your question is outside the scope of this system.\n"
            f"Reason: {gate['reason']}\n\n"
            f"This assistant only answers questions about **chemistry, chemoinformatics, dataset properties (Tox21), and biology**."
        )

    # Steps 2 & 3: Librarian (Tox21) + Researcher
    lib_result = librarian(question)
    res_result = researcher(question)

    # Step 4: Constructor
    final = constructor(question, lib_result, res_result)
    return final

if __name__ == "__main__":
    while True:
        try:
            user_input = input("\n💬 Ask a question (or type 'exit'): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        answer = run_pipeline(user_input)
        print(f"\n💡 FINAL RESPONSE:\n{answer}")
        print(f"\n{'─'*60}")
