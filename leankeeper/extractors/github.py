"""
LeanKeeper — GitHub extractor.

Extracts PRs, reviews, review comments and issue comments
via the GraphQL API (bulk) and REST API (supplements).
"""

import logging
import time
from datetime import datetime, timezone

import requests

from leankeeper.config import (
    BATCH_SIZE,
    GITHUB_GRAPHQL_URL,
    GITHUB_REPO_NAME,
    GITHUB_REPO_OWNER,
    GITHUB_REST_URL,
    GITHUB_SLEEP_BETWEEN_PAGES,
    GITHUB_TOKEN,
    MAX_PATCH_SIZE,
)
from leankeeper.models.database import (
    IssueComment,
    PullRequest,
    PullRequestFile,
    PullRequestLabel,
    Review,
    ReviewComment,
    init_db,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# GraphQL — PR extraction with reviews
# ──────────────────────────────────────────────

GRAPHQL_PRS_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(
      first: 50
      after: $cursor
      orderBy: {field: CREATED_AT, direction: DESC}
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      totalCount
      nodes {
        number
        title
        body
        author { login }
        state
        createdAt
        updatedAt
        mergedAt
        closedAt
        mergeCommit { oid }
        baseRefName
        headRefName
        additions
        deletions
        changedFiles
        labels(first: 20) {
          nodes { name }
        }
        reviews(first: 100) {
          nodes {
            databaseId
            author { login }
            state
            body
            submittedAt
          }
        }
        comments(first: 100) {
          nodes {
            databaseId
            author { login }
            body
            createdAt
            updatedAt
          }
        }
      }
    }
  }
}
"""


class GitHubExtractor:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }
        self._request_count = 0

    def _graphql(self, query: str, variables: dict) -> dict:
        """Execute a GraphQL query with rate limiting."""
        while True:
            self._request_count += 1
            response = requests.post(
                GITHUB_GRAPHQL_URL,
                headers=self.headers,
                json={"query": query, "variables": variables},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    logger.error(f"GraphQL errors: {data['errors']}")
                    raise RuntimeError(f"GraphQL errors: {data['errors']}")
                return data

            if response.status_code in (403, 429):
                reset = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset - time.time(), 10)
                logger.warning(f"Rate limited, waiting {wait:.0f}s...")
                time.sleep(wait)
                continue

            response.raise_for_status()

    def _rest_get(self, endpoint: str, params: dict = None) -> list | dict:
        """REST request with automatic pagination."""
        url = f"{GITHUB_REST_URL}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/{endpoint}"
        results = []
        page = 0

        server_errors = 0

        while url:
            self._request_count += 1
            page += 1

            for attempt in range(3):
                try:
                    response = requests.get(url, headers=self.headers, params=params, timeout=30)
                    break
                except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
                    if attempt < 2:
                        wait = 5 * (attempt + 1)
                        logger.warning(f"Network error ({e.__class__.__name__}), retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        raise

            if response.status_code in (403, 429):
                reset = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset - time.time(), 10)
                logger.warning(f"Rate limited, waiting {wait:.0f}s...")
                time.sleep(wait)
                continue

            if response.status_code >= 500:
                server_errors += 1
                if server_errors > 5:
                    logger.error(f"Too many server errors ({server_errors}), aborting. {len(results)} items fetched so far.")
                    break
                wait = 10 * server_errors
                logger.warning(f"Server error {response.status_code}, retrying in {wait}s... ({server_errors}/5)")
                time.sleep(wait)
                continue

            server_errors = 0  # Reset on success

            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                results.extend(data)
                if page % 10 == 0:
                    logger.info(f"REST {endpoint}: page {page}, {len(results)} items fetched")
            else:
                return data

            # Pagination via Link header
            url = None
            if "Link" in response.headers:
                for part in response.headers["Link"].split(","):
                    if 'rel="next"' in part:
                        url = part.split(";")[0].strip(" <>")
                        break

            params = None  # Params are embedded in the pagination URL
            time.sleep(GITHUB_SLEEP_BETWEEN_PAGES)

        return results

    # ──────────────────────────────────────────
    # PR extraction (GraphQL)
    # ──────────────────────────────────────────

    def extract_pull_requests(self):
        """Extract all PRs with reviews and issue comments."""
        logger.info("Extracting pull requests via GraphQL...")

        cursor = None
        total_extracted = 0

        while True:
            variables = {
                "owner": GITHUB_REPO_OWNER,
                "name": GITHUB_REPO_NAME,
                "cursor": cursor,
            }

            data = self._graphql(GRAPHQL_PRS_QUERY, variables)
            pr_data = data["data"]["repository"]["pullRequests"]
            total_count = pr_data["totalCount"]
            nodes = pr_data["nodes"]

            with self.session_factory() as session:
                for node in nodes:
                    self._upsert_pr(session, node)
                session.commit()

            total_extracted += len(nodes)
            logger.info(f"PRs: {total_extracted}/{total_count}")

            if not pr_data["pageInfo"]["hasNextPage"]:
                break

            cursor = pr_data["pageInfo"]["endCursor"]
            time.sleep(GITHUB_SLEEP_BETWEEN_PAGES)

        logger.info(f"PR extraction done: {total_extracted} PRs, {self._request_count} requests")

    def _upsert_pr(self, session, node: dict):
        """Insert or update a PR and its relations."""
        pr_number = node["number"]

        pr = session.get(PullRequest, pr_number)
        if pr is None:
            pr = PullRequest(number=pr_number)
            session.add(pr)

        pr.title = node["title"]
        pr.body = node.get("body")
        pr.author = node["author"]["login"] if node.get("author") else "[deleted]"
        state = node["state"].lower()
        # Bors closes PRs then merges separately — GitHub doesn't mark them as "merged"
        if state == "closed" and node["title"].startswith("[Merged by Bors]"):
            state = "merged"
        pr.state = state
        pr.created_at = _parse_dt(node["createdAt"])
        pr.updated_at = _parse_dt(node.get("updatedAt"))
        pr.merged_at = _parse_dt(node.get("mergedAt"))
        pr.closed_at = _parse_dt(node.get("closedAt"))
        pr.merge_commit_sha = node.get("mergeCommit", {}).get("oid") if node.get("mergeCommit") else None
        pr.base_branch = node.get("baseRefName")
        pr.head_branch = node.get("headRefName")
        pr.additions = node.get("additions", 0)
        pr.deletions = node.get("deletions", 0)
        pr.changed_files_count = node.get("changedFiles", 0)

        # Labels
        for label_node in node.get("labels", {}).get("nodes", []):
            if not any(l.name == label_node["name"] for l in pr.labels):
                pr.labels.append(PullRequestLabel(name=label_node["name"]))

        # Reviews
        for review_node in node.get("reviews", {}).get("nodes", []):
            review_id = review_node.get("databaseId")
            if review_id and not session.get(Review, review_id):
                session.add(Review(
                    id=review_id,
                    pr_number=pr_number,
                    author=review_node["author"]["login"] if review_node.get("author") else "[deleted]",
                    state=review_node["state"],
                    body=review_node.get("body"),
                    submitted_at=_parse_dt(review_node["submittedAt"]),
                ))

        # Issue comments (general comments)
        for comment_node in node.get("comments", {}).get("nodes", []):
            comment_id = comment_node.get("databaseId")
            if comment_id and not session.get(IssueComment, comment_id):
                session.add(IssueComment(
                    id=comment_id,
                    pr_number=pr_number,
                    author=comment_node["author"]["login"] if comment_node.get("author") else "[deleted]",
                    body=comment_node["body"],
                    created_at=_parse_dt(comment_node["createdAt"]),
                    updated_at=_parse_dt(comment_node.get("updatedAt")),
                ))

    # ──────────────────────────────────────────
    # Inline review comments (REST — not available in GraphQL with diff_hunk)
    # ──────────────────────────────────────────

    def extract_review_comments(self):
        """
        Extract all inline review comments via the REST API.
        This is the most valuable data: comments on specific code lines.
        Uses `since` parameter to resume from the last extracted comment.
        """
        # Find the latest comment date to resume from
        since = None
        with self.session_factory() as session:
            from sqlalchemy import func
            latest = session.query(func.max(ReviewComment.created_at)).scalar()
            if latest:
                since = latest.strftime("%Y-%m-%dT%H:%M:%SZ")
                logger.info(f"Resuming review comments from {since}")

        total_count = 0

        while True:
            params = {"per_page": 100, "sort": "created", "direction": "asc"}
            if since:
                params["since"] = since

            logger.info(f"Extracting inline review comments via REST{f' (since {since})' if since else ''}...")
            comments = self._rest_get("pulls/comments", params=params)

            if not comments:
                break

            count = 0
            last_date = None
            with self.session_factory() as session:
                for c in comments:
                    comment_id = c["id"]
                    if session.get(ReviewComment, comment_id):
                        last_date = c["created_at"]
                        continue

                    # Extract PR number from URL
                    pr_number = _extract_pr_number(c.get("pull_request_url", ""))
                    if not pr_number:
                        continue

                    session.add(ReviewComment(
                        id=comment_id,
                        pr_number=pr_number,
                        review_id=c.get("pull_request_review_id"),
                        author=c["user"]["login"] if c.get("user") else "[deleted]",
                        body=c["body"],
                        filepath=c.get("path"),
                        line=c.get("line"),
                        original_line=c.get("original_line"),
                        diff_hunk=c.get("diff_hunk"),
                        created_at=_parse_dt(c["created_at"]),
                        updated_at=_parse_dt(c.get("updated_at")),
                        in_reply_to_id=c.get("in_reply_to_id"),
                    ))
                    count += 1
                    last_date = c["created_at"]

                    if count % BATCH_SIZE == 0:
                        session.commit()
                        logger.info(f"Review comments: {total_count + count} inserted")

                session.commit()

            total_count += count
            logger.info(f"Review comments batch done: {count} new, {total_count} total")

            # If we got fewer items than expected or no new ones, we're done
            if count == 0 or not last_date:
                break

            # Resume from the last comment date for next batch
            since = last_date

        logger.info(f"Review comments done: {total_count} new comments")

    # ──────────────────────────────────────────
    # Files modified per PR (REST)
    # ──────────────────────────────────────────

    def extract_pr_files(self, pr_numbers: list[int] = None):
        """
        Extract modified files + patches for each PR.
        If pr_numbers is None, extracts for all PRs in the database.
        """
        with self.session_factory() as session:
            if pr_numbers is None:
                pr_numbers = [pr.number for pr in session.query(PullRequest.number).all()]

        logger.info(f"Extracting files for {len(pr_numbers)} PRs...")

        count = 0
        for i, pr_number in enumerate(pr_numbers):
            try:
                files = self._rest_get(f"pulls/{pr_number}/files", params={"per_page": 100})
            except requests.exceptions.HTTPError as e:
                logger.warning(f"PR #{pr_number}: {e}")
                continue

            with self.session_factory() as session:
                # Delete existing files for this PR
                session.query(PullRequestFile).filter_by(pr_number=pr_number).delete()

                for f in files:
                    patch = f.get("patch", "")
                    if len(patch) > MAX_PATCH_SIZE:
                        patch = patch[:MAX_PATCH_SIZE] + "\n... [truncated]"

                    session.add(PullRequestFile(
                        pr_number=pr_number,
                        filepath=f["filename"],
                        status=f.get("status"),
                        additions=f.get("additions", 0),
                        deletions=f.get("deletions", 0),
                        patch=patch,
                    ))
                    count += 1

                session.commit()

            if (i + 1) % 100 == 0:
                logger.info(f"PR files: {i + 1}/{len(pr_numbers)} PRs processed ({count} files)")

            time.sleep(GITHUB_SLEEP_BETWEEN_PAGES)

        logger.info(f"PR files done: {count} files for {len(pr_numbers)} PRs")

    # ──────────────────────────────────────────
    # Orchestrator
    # ──────────────────────────────────────────

    def extract_all(self, include_pr_files: bool = False):
        """
        Full extraction.
        include_pr_files=True is slow (~20,000 REST requests) but provides patches.
        """
        self.extract_pull_requests()
        self.extract_review_comments()
        if include_pr_files:
            self.extract_pr_files()

        logger.info(f"GitHub extraction done. Total requests: {self._request_count}")


# ──────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _extract_pr_number(url: str) -> int | None:
    """Extract PR number from a GitHub URL."""
    if not url:
        return None
    try:
        return int(url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        return None
