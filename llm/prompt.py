def build_prompt(query, contexts):
    """
    Build grounded prompt with citation enforcement.
    """

    context_text = "\n\n".join(
        [f"[Source: {doc['doc_id']}]\n{doc['content']}" for doc in contexts]
    )

    prompt = f"""
You are an enterprise AI governance assistant.

STRICT RULES:
- Answer ONLY using the provided context.
- You MUST cite sources using the format (Source: DOCUMENT_NAME).
- Keep one space after the colon in each citation.
- If answer not found in context, respond:
  "Insufficient information in provided documents."
- Keep answer structured and concise.

========================
CONTEXT:
{context_text}
========================

QUESTION:
{query}

Provide answer with citations.
"""

    return prompt
