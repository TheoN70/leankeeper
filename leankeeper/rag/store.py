"""
LeanKeeper — Vector store using pgvector.

Handles indexing and similarity search on PostgreSQL with the pgvector extension.
"""

import logging

from sqlalchemy import text

from leankeeper.config import EMBEDDING_MODEL, RAG_BATCH_SIZE, VECTOR_DIMENSION
from leankeeper.models.database import (
    Declaration,
    IssueComment,
    PullRequest,
    Review,
    ReviewComment,
    ZulipMessage,
)
from leankeeper.rag.embedder import Embedder

logger = logging.getLogger(__name__)

# Minimum text length per table (filter noisy short messages)
MIN_TEXT_LENGTH = {
    "zulip_messages": 50,
    "reviews": 30,
    "issue_comments": 30,
    "review_comments": 10,
    "pull_requests": 10,
    "declarations": 10,
}
DEFAULT_MIN_TEXT_LENGTH = 10

# How to build text from each source table
TEXT_BUILDERS = {
    "review_comments": lambda row: f"{row.author} on {row.filepath or 'PR'}:\n{row.body}",
    "zulip_messages": lambda row: f"[{row.topic}] {row.sender_name}:\n{row.content}",
    "pull_requests": lambda row: f"PR #{row.number}: {row.title}\n{row.body or ''}",
    "reviews": lambda row: f"{row.author} {row.state} on PR#{row.pr_number}:\n{row.body or ''}",
    "issue_comments": lambda row: f"{row.author} on PR#{row.pr_number}:\n{row.body}",
    "declarations": lambda row: f"{row.name}: {row.type_signature or ''}\n{row.docstring or ''}",
}

SOURCE_MODELS = {
    "review_comments": ReviewComment,
    "zulip_messages": ZulipMessage,
    "pull_requests": PullRequest,
    "reviews": Review,
    "issue_comments": IssueComment,
    "declarations": Declaration,
}

# Primary key column name per table
SOURCE_PK = {
    "review_comments": "id",
    "zulip_messages": "id",
    "pull_requests": "number",
    "reviews": "id",
    "issue_comments": "id",
    "declarations": "name",
}

# Date column name per table (for temporal filtering)
SOURCE_DATE = {
    "review_comments": "created_at",
    "zulip_messages": "timestamp",
    "pull_requests": "created_at",
    "reviews": "submitted_at",
    "issue_comments": "created_at",
    "declarations": None,  # No date for declarations
}


def init_pgvector(session_factory):
    """Create pgvector extension and embeddings table with vector column."""
    with session_factory() as session:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Drop and recreate to ensure vector column exists
        # (SQLAlchemy create_all may have created it without the vector column)
        has_vector = session.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'embeddings' AND column_name = 'embedding'
        """)).fetchone()

        if not has_vector:
            session.execute(text("DROP TABLE IF EXISTS embeddings"))
            session.execute(text(f"""
                CREATE TABLE embeddings (
                    id SERIAL PRIMARY KEY,
                    source_table VARCHAR(50) NOT NULL,
                    source_id VARCHAR(500) NOT NULL,
                    text TEXT NOT NULL,
                    embedding vector({VECTOR_DIMENSION})
                )
            """))

        session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_embeddings_source
            ON embeddings (source_table, source_id)
        """))

        # Add created_at column if missing (for temporal filtering in eval)
        has_created_at = session.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'embeddings' AND column_name = 'created_at'
        """)).fetchone()

        if not has_created_at:
            session.execute(text("ALTER TABLE embeddings ADD COLUMN created_at TIMESTAMP"))
            session.execute(text("CREATE INDEX IF NOT EXISTS ix_embeddings_created_at ON embeddings (created_at)"))
            logger.info("Added created_at column to embeddings")

        session.commit()
    logger.info("pgvector initialized")


def index_table(session_factory, table_name: str, update_only: bool = False):
    """Index all rows from a source table into the embeddings table."""
    if table_name not in SOURCE_MODELS:
        raise ValueError(f"Unknown table: {table_name}. Available: {list(SOURCE_MODELS.keys())}")

    model = SOURCE_MODELS[table_name]
    pk_col = SOURCE_PK[table_name]
    date_col = SOURCE_DATE[table_name]
    text_builder = TEXT_BUILDERS[table_name]

    # Quick check: skip if nothing new to index
    if update_only:
        with session_factory() as session:
            source_count = session.query(model).count()
            embedded_count = session.execute(
                text("SELECT COUNT(*) FROM embeddings WHERE source_table = :t"),
                {"t": table_name},
            ).scalar()
        if embedded_count >= source_count:
            logger.info(f"Indexing {table_name}: already up to date ({embedded_count} embeddings)")
            return

    embedder = Embedder(EMBEDDING_MODEL)

    # Phase 1: Read all rows (IDs + text + date) into memory
    logger.info(f"Indexing {table_name}: reading rows...")
    rows_to_embed = []

    with session_factory() as session:
        if update_only:
            existing_ids = set(
                r[0] for r in session.execute(
                    text("SELECT source_id FROM embeddings WHERE source_table = :t"),
                    {"t": table_name},
                ).fetchall()
            )
        else:
            existing_ids = set()

        for row in session.query(model).yield_per(1000):
            source_id = str(getattr(row, pk_col))

            if source_id in existing_ids:
                continue

            row_text = text_builder(row)
            min_len = MIN_TEXT_LENGTH.get(table_name, DEFAULT_MIN_TEXT_LENGTH)
            if not row_text or len(row_text.strip()) < min_len:
                continue

            if len(row_text) > 2000:
                row_text = row_text[:2000]

            row_date = getattr(row, date_col, None) if date_col else None
            rows_to_embed.append((source_id, row_text, row_date))

    total = len(rows_to_embed)
    logger.info(f"Indexing {table_name}: {total} rows to embed")

    if not total:
        return

    # Phase 2: Embed and insert in batches
    count = 0
    for i in range(0, total, RAG_BATCH_SIZE):
        batch = rows_to_embed[i:i + RAG_BATCH_SIZE]
        batch_ids = [r[0] for r in batch]
        batch_texts = [r[1] for r in batch]
        batch_dates = [r[2] for r in batch]

        with session_factory() as session:
            _flush_batch(session, embedder, table_name, batch_texts, batch_ids, batch_dates)

        count += len(batch)
        if count % 5000 == 0 or count == total:
            logger.info(f"  {table_name}: {count}/{total} indexed")

    logger.info(f"Indexing {table_name} done: {count} embedded")


def _flush_batch(session, embedder, table_name, texts, ids, dates=None):
    """Embed and upsert a batch."""
    embeddings = embedder.embed(texts)
    if dates is None:
        dates = [None] * len(texts)

    for source_id, txt, emb, dt in zip(ids, texts, embeddings, dates):
        emb_str = "[" + ",".join(str(x) for x in emb) + "]"
        session.execute(
            text("""
                INSERT INTO embeddings (source_table, source_id, text, embedding, created_at)
                VALUES (:table, :id, :text, :embedding, :created_at)
                ON CONFLICT (source_table, source_id)
                DO UPDATE SET text = :text, embedding = :embedding, created_at = :created_at
            """),
            {"table": table_name, "id": source_id, "text": txt, "embedding": emb_str, "created_at": dt},
        )
    session.commit()


def search(session_factory, query: str, source_tables: list[str] = None, limit: int = 10,
           before_date=None, min_similarity: float = 0.45):
    """Semantic search across embeddings.

    Args:
        before_date: If set, only return embeddings created before this date.
                     Used for evaluation to prevent temporal data leakage.
        min_similarity: Minimum cosine similarity threshold. Results below this are filtered out.
    """
    embedder = Embedder(EMBEDDING_MODEL)
    query_emb = embedder.embed_one(query)
    emb_str = "[" + ",".join(str(x) for x in query_emb) + "]"

    conditions = []
    params = {"embedding": emb_str, "limit": limit}

    if source_tables:
        placeholders = ", ".join(f":t{i}" for i in range(len(source_tables)))
        conditions.append(f"source_table IN ({placeholders})")
        for i, t in enumerate(source_tables):
            params[f"t{i}"] = t

    if before_date is not None:
        conditions.append("created_at < :before_date")
        params["before_date"] = before_date

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT source_table, source_id, text,
               1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM embeddings
        {where}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
    """

    with session_factory() as session:
        results = session.execute(text(sql), params).fetchall()

    return [
        {"source_table": r[0], "source_id": r[1], "text": r[2], "similarity": round(r[3], 4)}
        for r in results
        if r[3] >= min_similarity
    ]


def delete(session_factory, source_table: str = None, source_id: str = None):
    """Delete embeddings by source table and/or source ID."""
    with session_factory() as session:
        if source_table and source_id:
            result = session.execute(
                text("DELETE FROM embeddings WHERE source_table = :t AND source_id = :id"),
                {"t": source_table, "id": source_id},
            )
        elif source_table:
            result = session.execute(
                text("DELETE FROM embeddings WHERE source_table = :t"),
                {"t": source_table},
            )
        else:
            result = session.execute(text("DELETE FROM embeddings"))
        session.commit()
        return result.rowcount


def status(session_factory):
    """Return embedding counts per source table."""
    with session_factory() as session:
        results = session.execute(
            text("SELECT source_table, COUNT(*) FROM embeddings GROUP BY source_table ORDER BY source_table")
        ).fetchall()
    return {r[0]: r[1] for r in results}
