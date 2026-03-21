"""
LeanKeeper — Database models.

All tables for storing data extracted from:
- Git (commits, diffs)
- GitHub API (PRs, reviews, review comments)
- Zulip (messages, channels, topics)
- Lean/Mathlib (declarations, imports, typeclasses)

Uses SQLAlchemy with PostgreSQL.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
# Git
# ──────────────────────────────────────────────


class Commit(Base):
    __tablename__ = "commits"

    sha = Column(String(40), primary_key=True)
    author_name = Column(String(255), nullable=False)
    author_email = Column(String(255))
    date = Column(DateTime, nullable=False, index=True)
    message = Column(Text, nullable=False)
    insertions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)

    files = relationship("CommitFile", back_populates="commit", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Commit {self.sha[:8]} {self.message[:50]}>"


class CommitFile(Base):
    """Files modified per commit, with diff."""

    __tablename__ = "commit_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    commit_sha = Column(String(40), ForeignKey("commits.sha"), nullable=False, index=True)
    filepath = Column(Text, nullable=False)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    patch = Column(Text)  # File diff (can be large)

    commit = relationship("Commit", back_populates="files")

    __table_args__ = (Index("ix_commit_files_path", "filepath"),)


# ──────────────────────────────────────────────
# GitHub — Pull Requests
# ──────────────────────────────────────────────


class PullRequest(Base):
    __tablename__ = "pull_requests"

    number = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    body = Column(Text)  # Markdown description
    author = Column(String(255), nullable=False, index=True)
    state = Column(String(20), nullable=False, index=True)  # open, closed, merged
    created_at = Column(DateTime, nullable=False, index=True)
    updated_at = Column(DateTime)
    merged_at = Column(DateTime)
    closed_at = Column(DateTime)
    merge_commit_sha = Column(String(40))
    base_branch = Column(String(255))
    head_branch = Column(String(255))
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    changed_files_count = Column(Integer, default=0)

    labels = relationship("PullRequestLabel", back_populates="pull_request", cascade="all, delete-orphan")
    files = relationship("PullRequestFile", back_populates="pull_request", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="pull_request", cascade="all, delete-orphan")
    review_comments = relationship("ReviewComment", back_populates="pull_request", cascade="all, delete-orphan")
    issue_comments = relationship("IssueComment", back_populates="pull_request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PR #{self.number} {self.title[:50]}>"


class PullRequestLabel(Base):
    __tablename__ = "pull_request_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_number = Column(Integer, ForeignKey("pull_requests.number"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)

    pull_request = relationship("PullRequest", back_populates="labels")


class PullRequestFile(Base):
    """Files modified in a PR, with patch."""

    __tablename__ = "pull_request_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_number = Column(Integer, ForeignKey("pull_requests.number"), nullable=False, index=True)
    filepath = Column(Text, nullable=False)
    status = Column(String(20))  # added, removed, modified, renamed
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    patch = Column(Text)  # The diff

    pull_request = relationship("PullRequest", back_populates="files")

    __table_args__ = (Index("ix_pr_files_path", "filepath"),)


# ──────────────────────────────────────────────
# GitHub — Reviews and comments
# ──────────────────────────────────────────────


class Review(Base):
    """Top-level PR review (approve, request changes, comment)."""

    __tablename__ = "reviews"

    id = Column(BigInteger, primary_key=True)  # GitHub review ID
    pr_number = Column(Integer, ForeignKey("pull_requests.number"), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    state = Column(String(30), nullable=False, index=True)  # APPROVED, CHANGES_REQUESTED, COMMENTED
    body = Column(Text)
    submitted_at = Column(DateTime, nullable=False)

    pull_request = relationship("PullRequest", back_populates="reviews")

    def __repr__(self):
        return f"<Review #{self.id} {self.state} on PR#{self.pr_number}>"


class ReviewComment(Base):
    """Inline comment on a specific code line in a PR. The most valuable data."""

    __tablename__ = "review_comments"

    id = Column(BigInteger, primary_key=True)  # GitHub comment ID
    pr_number = Column(Integer, ForeignKey("pull_requests.number"), nullable=False, index=True)
    review_id = Column(BigInteger, ForeignKey("reviews.id"), index=True)  # Can be null
    author = Column(String(255), nullable=False, index=True)
    body = Column(Text, nullable=False)
    filepath = Column(Text)  # Commented file
    line = Column(Integer)  # Commented line
    original_line = Column(Integer)
    diff_hunk = Column(Text)  # Diff context around the comment
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)
    in_reply_to_id = Column(BigInteger)  # For discussion threads

    pull_request = relationship("PullRequest", back_populates="review_comments")

    __table_args__ = (Index("ix_review_comments_path", "filepath"),)

    def __repr__(self):
        return f"<ReviewComment #{self.id} on {self.filepath}>"


class IssueComment(Base):
    """General comment on a PR (not inline on code)."""

    __tablename__ = "issue_comments"

    id = Column(BigInteger, primary_key=True)  # GitHub comment ID
    pr_number = Column(Integer, ForeignKey("pull_requests.number"), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime)

    pull_request = relationship("PullRequest", back_populates="issue_comments")


# ──────────────────────────────────────────────
# Zulip
# ──────────────────────────────────────────────


class ZulipChannel(Base):
    __tablename__ = "zulip_channels"

    id = Column(BigInteger, primary_key=True)  # Zulip stream ID
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)

    messages = relationship("ZulipMessage", back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ZulipChannel #{self.name}>"


class ZulipMessage(Base):
    __tablename__ = "zulip_messages"

    id = Column(BigInteger, primary_key=True)  # Zulip message ID
    channel_id = Column(BigInteger, ForeignKey("zulip_channels.id"), nullable=False, index=True)
    topic = Column(String(500), nullable=False, index=True)
    sender_name = Column(String(255), nullable=False, index=True)
    sender_email = Column(String(255))
    content = Column(Text, nullable=False)  # Markdown
    timestamp = Column(DateTime, nullable=False, index=True)

    channel = relationship("ZulipChannel", back_populates="messages")

    __table_args__ = (Index("ix_zulip_messages_channel_topic", "channel_id", "topic"),)

    def __repr__(self):
        return f"<ZulipMessage #{self.id} in {self.topic[:30]}>"


# ──────────────────────────────────────────────
# Lean / Mathlib — Declarations
# ──────────────────────────────────────────────


class Declaration(Base):
    """A Lean declaration in Mathlib (theorem, def, instance, class, structure...)."""

    __tablename__ = "declarations"

    name = Column(String(500), primary_key=True)  # e.g. "Finset.sum_comm"
    kind = Column(String(30), nullable=False, index=True)  # theorem, def, instance, class, structure, lemma
    filepath = Column(Text, nullable=False, index=True)
    line = Column(Integer)
    type_signature = Column(Text)  # Full type
    docstring = Column(Text)
    is_public = Column(Boolean, default=True)
    namespace = Column(String(500), index=True)  # e.g. "Finset"

    def __repr__(self):
        return f"<Declaration {self.kind} {self.name}>"


class Import(Base):
    """Edge in the Mathlib import graph."""

    __tablename__ = "imports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(Text, nullable=False, index=True)  # The importing file
    target_file = Column(Text, nullable=False, index=True)  # The imported file

    __table_args__ = (Index("ix_imports_edge", "source_file", "target_file", unique=True),)


class TypeclassInstance(Base):
    """Typeclass instance in Mathlib."""

    __tablename__ = "typeclass_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_name = Column(String(500), nullable=False, index=True)
    class_name = Column(String(500), nullable=False, index=True)  # The typeclass
    type_args = Column(Text)  # Type arguments
    filepath = Column(Text)
    line = Column(Integer)

    __table_args__ = (Index("ix_typeclass_class", "class_name"),)


class TypeclassParent(Base):
    """Typeclass hierarchy (extends)."""

    __tablename__ = "typeclass_parents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    child_class = Column(String(500), nullable=False, index=True)
    parent_class = Column(String(500), nullable=False, index=True)

    __table_args__ = (Index("ix_typeclass_hierarchy", "child_class", "parent_class", unique=True),)


# ──────────────────────────────────────────────
# Database setup
# ──────────────────────────────────────────────

ALL_TABLES = [
    Commit,
    CommitFile,
    PullRequest,
    PullRequestLabel,
    PullRequestFile,
    Review,
    ReviewComment,
    IssueComment,
    ZulipChannel,
    ZulipMessage,
    Declaration,
    Import,
    TypeclassInstance,
    TypeclassParent,
]


def init_db(database_url: str | None = None) -> sessionmaker:
    """Create all tables and return a sessionmaker."""
    from leankeeper.config import DATABASE_URL as DEFAULT_URL

    url = database_url or DEFAULT_URL
    engine = create_engine(url, echo=False, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
