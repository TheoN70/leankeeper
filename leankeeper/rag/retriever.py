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
        backend: str = None, before_date=None, exclude_source_ids: set[str] = None) -> str:
    """
    Full RAG pipeline: retrieve context, build prompt, generate response.

    Args:
        query: The user's question or code to review.
        mode: "contributor" or "reviewer".
        limit: Number of similar items to retrieve.
        backend: LLM backend override (claude, openai, ollama).
        before_date: Only use data before this date (for evaluation).
        exclude_source_ids: Source IDs to exclude from search (prevent self-referencing).
    """
    # Retrieve relevant context
    if mode == "reviewer":
        sources = ["review_comments", "reviews"]
    else:
        sources = ["review_comments", "zulip_messages", "pull_requests"]

    results = store.search(session_factory, query, source_tables=sources, limit=limit,
                           before_date=before_date, exclude_source_ids=exclude_source_ids)

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


def build_context_md(session_factory, query: str, mode: str = "contributor",
                     limit: int = 10, include_project: bool = True) -> str:
    """
    Build a markdown context file for use with Claude Code or other tools.

    Args:
        query: The user's question.
        mode: "contributor" or "reviewer".
        limit: Number of similar items to retrieve.
        include_project: If True, include project context (conventions, wiki).
    """
    # Retrieve relevant context
    if mode == "reviewer":
        sources = ["review_comments", "reviews"]
    else:
        sources = ["review_comments", "zulip_messages", "pull_requests"]

    results = store.search(session_factory, query, source_tables=sources, limit=limit)

    # Build system prompt
    if mode == "reviewer":
        system = build_reviewer_prompt(_format_context(results) if results else "(No examples found.)")
    else:
        system = build_contributor_prompt(_format_context(results) if results else "(No examples found.)")

    parts = [f"# LeanKeeper RAG Context\n"]
    parts.append(f"**Mode:** {mode}")
    parts.append(f"**Query:** {query}\n")

    if include_project:
        import os
        # Include BASE_CONTEXT.md (comprehensive AI reference for Mathlib contributions)
        base_context = os.path.join(os.path.dirname(__file__), "..", "..", "BASE_CONTEXT.md")
        if os.path.exists(base_context):
            with open(base_context, "r") as f:
                parts.append(f.read())
            parts.append("")
        else:
            parts.append("## Project Context\n")
            parts.append("This is a contribution to [Mathlib](https://github.com/leanprover-community/mathlib4), ")
            parts.append("the community library of formalized mathematics in Lean 4.\n")

    parts.append("## System Prompt\n")
    parts.append(system)
    parts.append("")

    parts.append("## User Query\n")
    parts.append(query)

    return "\n".join(parts)
