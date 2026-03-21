# Database Architecture

PostgreSQL database managed via SQLAlchemy ORM. All models defined in `leankeeper/models/database.py`.

Tables are auto-created by `init_db()` via `Base.metadata.create_all()`. External IDs from GitHub and Zulip APIs use `BigInteger` (64-bit) since they exceed PostgreSQL's 32-bit integer max (2,147,483,647).

## Schema Overview

```
                        ┌──────────────────┐
                        │  pull_requests   │
                        │  PK: number      │
                        └────────┬─────────┘
                                 │ 1:N
          ┌──────────┬───────────┼───────────┬──────────────┐
          ▼          ▼           ▼           ▼              ▼
   ┌──────────┐ ┌─────────┐ ┌────────┐ ┌─────────┐ ┌────────────┐
   │ reviews  │ │ review_ │ │ issue_ │ │   pr_   │ │    pr_     │
   │          │ │comments │ │comments│ │ labels  │ │   files    │
   └────┬─────┘ └─────────┘ └────────┘ └─────────┘ └────────────┘
        │ 1:N        ▲
        └────────────┘
         FK: review_id

  ┌──────────┐        ┌────────────────┐
  │ commits  │ 1:N    │  commit_files  │
  │ PK: sha  │───────▶│  FK: commit_sha│
  └──────────┘        └────────────────┘

  ┌────────────────┐        ┌─────────────────┐
  │ zulip_channels │ 1:N    │ zulip_messages  │
  │ PK: id         │───────▶│ FK: channel_id  │
  └────────────────┘        └─────────────────┘

  ┌──────────────┐  ┌─────────┐  ┌─────────────────────┐  ┌────────────────────┐
  │ declarations │  │ imports │  │ typeclass_instances  │  │ typeclass_parents  │
  │ PK: name     │  │         │  │                     │  │                    │
  └──────────────┘  └─────────┘  └─────────────────────┘  └────────────────────┘
  └──────────── Lean/Mathlib (schema only, not yet populated) ──────────────────┘
```

## Tables

### Git

#### `commits`

Extracted by `extract git`. One row per git commit in the mathlib4 repository.

| Column       | Type         | Constraints     | Description                  |
|--------------|--------------|-----------------|------------------------------|
| sha          | String(40)   | **PK**          | Full commit hash             |
| author_name  | String(255)  | NOT NULL        | Git author name              |
| author_email | String(255)  |                 | Git author email             |
| date         | DateTime     | NOT NULL, INDEX | Author date                  |
| message      | Text         | NOT NULL        | Commit subject line          |
| insertions   | Integer      | default 0       | Total lines added            |
| deletions    | Integer      | default 0       | Total lines removed          |

#### `commit_files`

Extracted by `extract git` (stats) and optionally `extract git-patches` (patch content). One row per file modified in a commit.

| Column     | Type       | Constraints          | Description                          |
|------------|------------|----------------------|--------------------------------------|
| id         | Integer    | **PK**, autoincrement|                                      |
| commit_sha | String(40) | NOT NULL, FK, INDEX  | → `commits.sha`                     |
| filepath   | Text       | NOT NULL, INDEX      | File path in the repository          |
| additions  | Integer    | default 0            | Lines added in this file             |
| deletions  | Integer    | default 0            | Lines removed in this file           |
| patch      | Text       |                      | Full diff (optional, can be large)   |

Indexes: `ix_commit_files_path` on `filepath`.

---

### GitHub — Pull Requests

#### `pull_requests`

Extracted by `extract github`. Central table linking all PR-related data.

| Column             | Type        | Constraints     | Description                                  |
|--------------------|-------------|-----------------|----------------------------------------------|
| number             | Integer     | **PK**          | GitHub PR number                             |
| title              | Text        | NOT NULL        | PR title                                     |
| body               | Text        |                 | PR description (markdown)                    |
| author             | String(255) | NOT NULL, INDEX | GitHub login of the author                   |
| state              | String(20)  | NOT NULL, INDEX | `open`, `closed`, or `merged`                |
| created_at         | DateTime    | NOT NULL, INDEX | When the PR was created                      |
| updated_at         | DateTime    |                 | Last update                                  |
| merged_at          | DateTime    |                 | When merged (null if not merged)             |
| closed_at          | DateTime    |                 | When closed (null if still open)             |
| merge_commit_sha   | String(40)  |                 | Merge commit hash                            |
| base_branch        | String(255) |                 | Target branch (usually `master`/`main`)      |
| head_branch        | String(255) |                 | Source branch                                |
| additions          | Integer     | default 0       | Total lines added                            |
| deletions          | Integer     | default 0       | Total lines removed                          |
| changed_files_count| Integer     | default 0       | Number of files changed                      |

**Note on state**: Mathlib uses Bors to merge PRs. Bors closes the PR and pushes a separate merge commit, so GitHub does not mark them as `MERGED`. The extractor detects Bors-merged PRs by checking for the `[Merged by Bors]` title prefix and sets `state = "merged"`.

#### `pull_request_labels`

Extracted by `extract github` (embedded in PR GraphQL response).

| Column    | Type        | Constraints          | Description           |
|-----------|-------------|----------------------|-----------------------|
| id        | Integer     | **PK**, autoincrement|                       |
| pr_number | Integer     | NOT NULL, FK, INDEX  | → `pull_requests.number` |
| name      | String(255) | NOT NULL, INDEX      | Label name            |

#### `pull_request_files`

Extracted by `extract github-files`. One row per file modified in a PR, with the diff patch.

| Column    | Type       | Constraints          | Description                        |
|-----------|------------|----------------------|------------------------------------|
| id        | Integer    | **PK**, autoincrement|                                    |
| pr_number | Integer    | NOT NULL, FK, INDEX  | → `pull_requests.number`           |
| filepath  | Text       | NOT NULL, INDEX      | File path                          |
| status    | String(20) |                      | `added`, `removed`, `modified`, `renamed` |
| additions | Integer    | default 0            | Lines added                        |
| deletions | Integer    | default 0            | Lines removed                      |
| patch     | Text       |                      | Diff (truncated at 100K chars)     |

Indexes: `ix_pr_files_path` on `filepath`.

---

### GitHub — Reviews and Comments

#### `reviews`

Extracted by `extract github` (embedded in PR GraphQL response). One row per top-level PR review.

| Column       | Type        | Constraints     | Description                                    |
|--------------|-------------|-----------------|------------------------------------------------|
| id           | BigInteger  | **PK**          | GitHub review ID                               |
| pr_number    | Integer     | NOT NULL, FK, INDEX | → `pull_requests.number`                   |
| author       | String(255) | NOT NULL, INDEX | Reviewer GitHub login                          |
| state        | String(30)  | NOT NULL, INDEX | `APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`   |
| body         | Text        |                 | Review body text                               |
| submitted_at | DateTime    | NOT NULL        | When the review was submitted                  |

#### `review_comments`

Extracted by `extract github-reviews` (REST API). **The most valuable training data** — inline comments on specific code lines with diff context.

| Column          | Type        | Constraints     | Description                              |
|-----------------|-------------|-----------------|------------------------------------------|
| id              | BigInteger  | **PK**          | GitHub comment ID                        |
| pr_number       | Integer     | NOT NULL, FK, INDEX | → `pull_requests.number`             |
| review_id       | BigInteger  | FK, INDEX       | → `reviews.id` (can be null)            |
| author          | String(255) | NOT NULL, INDEX | Commenter GitHub login                   |
| body            | Text        | NOT NULL        | Comment text (markdown)                  |
| filepath        | Text        | INDEX           | File being commented on                  |
| line            | Integer     |                 | Line number in the new version           |
| original_line   | Integer     |                 | Line number in the original version      |
| diff_hunk       | Text        |                 | Diff context surrounding the comment     |
| created_at      | DateTime    | NOT NULL        | When the comment was posted              |
| updated_at      | DateTime    |                 | Last edit                                |
| in_reply_to_id  | BigInteger  |                 | Parent comment ID (for threaded replies) |

Indexes: `ix_review_comments_path` on `filepath`.

#### `issue_comments`

Extracted by `extract github` (embedded in PR GraphQL response). General conversation comments on PRs (not inline on code).

| Column     | Type        | Constraints          | Description               |
|------------|-------------|----------------------|---------------------------|
| id         | BigInteger  | **PK**               | GitHub comment ID         |
| pr_number  | Integer     | NOT NULL, FK, INDEX  | → `pull_requests.number`  |
| author     | String(255) | NOT NULL, INDEX      | Commenter GitHub login    |
| body       | Text        | NOT NULL             | Comment text (markdown)   |
| created_at | DateTime    | NOT NULL             | When posted               |
| updated_at | DateTime    |                      | Last edit                 |

---

### Zulip

#### `zulip_channels`

Extracted by `extract zulip`. Filtered to channels listed in `config.ZULIP_CHANNELS`.

| Column      | Type        | Constraints          | Description         |
|-------------|-------------|----------------------|---------------------|
| id          | BigInteger  | **PK**               | Zulip stream ID    |
| name        | String(255) | NOT NULL, UNIQUE, INDEX | Channel name    |
| description | Text        |                      | Channel description |

#### `zulip_messages`

Extracted by `extract zulip`. All messages from configured channels.

| Column       | Type        | Constraints          | Description                    |
|--------------|-------------|----------------------|--------------------------------|
| id           | BigInteger  | **PK**               | Zulip message ID              |
| channel_id   | BigInteger  | NOT NULL, FK, INDEX  | → `zulip_channels.id`         |
| topic        | String(500) | NOT NULL, INDEX      | Topic (thread) name           |
| sender_name  | String(255) | NOT NULL, INDEX      | Sender display name           |
| sender_email | String(255) |                      | Sender email                  |
| content      | Text        | NOT NULL             | Message content (markdown)    |
| timestamp    | DateTime    | NOT NULL, INDEX      | When the message was sent     |

Indexes: `ix_zulip_messages_channel_topic` on `(channel_id, topic)`.

---

### Lean / Mathlib (not yet populated)

These tables have their schema defined but are not yet populated by any extractor. They are planned for future phases.

#### `declarations`

Lean declarations in Mathlib (theorems, definitions, instances, classes, structures).

| Column         | Type        | Constraints     | Description                                |
|----------------|-------------|-----------------|--------------------------------------------|
| name           | String(500) | **PK**          | Fully qualified name (e.g. `Finset.sum_comm`) |
| kind           | String(30)  | NOT NULL, INDEX | `theorem`, `def`, `instance`, `class`, `structure`, `lemma` |
| filepath       | Text        | NOT NULL, INDEX | File path in Mathlib                       |
| line           | Integer     |                 | Line number                                |
| type_signature | Text        |                 | Full Lean type                             |
| docstring      | Text        |                 | Documentation string                       |
| is_public      | Boolean     | default True    | Whether publicly visible                   |
| namespace      | String(500) | INDEX           | Namespace (e.g. `Finset`)                  |

#### `imports`

Edges in the Mathlib import dependency graph.

| Column      | Type    | Constraints          | Description        |
|-------------|---------|----------------------|--------------------|
| id          | Integer | **PK**, autoincrement|                    |
| source_file | Text    | NOT NULL, INDEX      | The importing file |
| target_file | Text    | NOT NULL, INDEX      | The imported file  |

Indexes: `ix_imports_edge` unique on `(source_file, target_file)`.

#### `typeclass_instances`

Typeclass instances in Mathlib.

| Column        | Type        | Constraints          | Description              |
|---------------|-------------|----------------------|--------------------------|
| id            | Integer     | **PK**, autoincrement|                          |
| instance_name | String(500) | NOT NULL, INDEX      | Instance declaration name|
| class_name    | String(500) | NOT NULL, INDEX      | The typeclass            |
| type_args     | Text        |                      | Type arguments           |
| filepath      | Text        |                      | File path                |
| line          | Integer     |                      | Line number              |

Indexes: `ix_typeclass_class` on `class_name`.

#### `typeclass_parents`

Typeclass hierarchy (extends relationships).

| Column       | Type        | Constraints          | Description    |
|--------------|-------------|----------------------|----------------|
| id           | Integer     | **PK**, autoincrement|                |
| child_class  | String(500) | NOT NULL, INDEX      | Child typeclass|
| parent_class | String(500) | NOT NULL, INDEX      | Parent typeclass|

Indexes: `ix_typeclass_hierarchy` unique on `(child_class, parent_class)`.

## Extraction Commands and Table Mapping

| Command                  | Tables populated                                          |
|--------------------------|-----------------------------------------------------------|
| `extract github`         | `pull_requests`, `pull_request_labels`, `reviews`, `issue_comments` |
| `extract github-reviews` | `review_comments`                                         |
| `extract github-files`   | `pull_request_files`                                      |
| `extract git`            | `commits`, `commit_files` (stats only)                    |
| `extract git-patches`    | `commit_files` (adds `patch` column to existing rows)     |
| `extract zulip`          | `zulip_channels`, `zulip_messages`                        |
| `extract all`            | All of the above except `github-files` and `git-patches`  |
