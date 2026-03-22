"""
LeanKeeper — High-level retrieval for RAG.

Combines vector search with context formatting.
"""

import logging

from leankeeper.rag import store
from leankeeper.rag.llm import get_llm
from leankeeper.rag.prompt import build_contributor_prompt, build_reviewer_prompt

logger = logging.getLogger(__name__)


def _format_context(results: list[dict]) -> str:
    """Format search results as context for the LLM."""
    parts = []
    for i, r in enumerate(results, 1):
        source = r["source_table"].replace("_", " ")
        parts.append(f"--- Example {i} ({source}, similarity: {r['similarity']}) ---\n{r['text']}")
    return "\n\n".join(parts)


def ask(session_factory, query: str, mode: str = "contributor", limit: int = 10,
        backend: str = None, exclude_pr: int = None) -> str:
    """
    Full RAG pipeline: retrieve context, build prompt, generate response.

    Args:
        query: The user's question or code to review.
        mode: "contributor" or "reviewer".
        limit: Number of similar items to retrieve.
        backend: LLM backend override (claude, openai, ollama).
        exclude_pr: Exclude data from this PR number (for evaluation).
    """
    # Retrieve relevant context
    if mode == "reviewer":
        sources = ["review_comments", "reviews"]
    else:
        sources = ["review_comments", "zulip_messages", "pull_requests"]

    results = store.search(session_factory, query, source_tables=sources, limit=limit,
                           exclude_pr=exclude_pr)

    if not results:
        logger.warning("No relevant context found in embeddings")
        context = "(No relevant examples found in the database.)"
    else:
        context = _format_context(results)

    # Build prompt
    if mode == "reviewer":
        system = build_reviewer_prompt(context)
    else:
        system = build_contributor_prompt(context)

    # Generate response
    llm = get_llm(backend)
    logger.info(f"Generating response with {llm.__class__.__name__}...")
    return llm.generate(system, query)
