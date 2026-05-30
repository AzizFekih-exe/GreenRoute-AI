import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def constructor(question: str, lib_result: dict, res_result: dict) -> str:
    """Synthesizes all agent outputs into a final answer for the user."""
    print("\n[CONSTRUCTOR] Building final response...")

    lib_ok = lib_result.get("success", False)
    res_ok = res_result.get("success", False)

    # Both failed → override
    if not lib_ok and not res_ok:
        override_msg = (
            f"⚠️ **[OVERRIDE — Both agents failed]**\n\n"
            f"- Librarian error: {lib_result.get('error','Unknown')}\n"
            f"- Researcher error: {res_result.get('error','Unknown')}\n\n"
            f"I was unable to retrieve information from either the local Tox21 dataset or the web. "
            f"Please try rephrasing your question or check system connectivity."
        )
        print("   [WARNING] Both agents failed — issuing OVERRIDE response.")
        return override_msg

    # Build context, noting partial failures
    context_sections = []
    override_notes   = []

    if lib_ok and lib_result["content"]:
        context_sections.append(f"=== TOX21 DATABASE ===\n{lib_result['content']}")
    else:
        override_notes.append(f"Librarian: {lib_result.get('error','No data')}")

    if res_ok and res_result["content"]:
        context_sections.append(f"=== WEB SEARCH ===\n{res_result['content']}")
    else:
        override_notes.append(f"Researcher: {res_result.get('error','No data')}")

    override_block = ""
    if override_notes:
        override_block = "\n\nNote: Some agents had issues: " + " | ".join(override_notes)

    combined_context = "\n\n".join(context_sections)

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are the Advanced Chemoinformatics Assistant Constructor.
Your job is to synthesize information from multiple sources and produce a clear, professional, well-structured answer.
Use the provided context. Be precise and cite which source supports each point (Tox21 dataset vs web).
If some context is missing, acknowledge it briefly but still give the best possible scientific answer.{override_block}

Context:
{combined_context}"""
                },
                {"role": "user", "content": question}
            ]
        )
        answer = response.choices[0].message.content

        # Build sources footer
        all_sources = []
        if lib_ok:
            all_sources += [f"📄 {s}" for s in lib_result.get("sources", [])]
        if res_ok:
            all_sources += [f"🌐 {s}" for s in res_result.get("sources", [])]

        source_block = ""
        if all_sources:
            source_block = "\n\n---\n**📚 Sources:**\n" + "\n".join(f"- {s}" for s in all_sources[:6])

        if override_notes:
            override_header = f"\n> ⚠️ *Partial override — the following agents had issues: {'; '.join(override_notes)}*\n\n"
            return override_header + answer + source_block
        return answer + source_block

    except Exception as e:
        print(f"   [ERROR] Constructor LLM error: {e}")
        return (
            f"⚠️ **[OVERRIDE — Constructor failed]**\n\n"
            f"Error: {e}\n\n"
            f"Raw data retrieved but could not be formatted. "
            f"Please try again."
        )
