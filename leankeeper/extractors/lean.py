"""
LeanKeeper — Lean declaration extractor.

Parses Lean 4 source files from the bare mathlib4 repo to extract
declarations (theorems, definitions, lemmas, instances, classes, structures)
with their type signatures and docstrings.
"""

import logging
import re
import subprocess
from pathlib import Path

from leankeeper.config import BATCH_SIZE, GIT_CLONE_DIR
from leankeeper.models.database import Declaration

logger = logging.getLogger(__name__)

# Keywords that start a declaration
DECL_KEYWORDS = {"theorem", "lemma", "def", "instance", "class", "structure", "abbrev"}

# Regex for docstrings: /-- ... -/
DOCSTRING_RE = re.compile(r"/--\s*(.*?)\s*-/", re.DOTALL)


class LeanExtractor:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.repo_dir = GIT_CLONE_DIR

    def _git(self, *args, timeout=60) -> str:
        """Run a git command on the bare repo."""
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout

    def list_lean_files(self) -> list[str]:
        """List all .lean files under Mathlib/."""
        output = self._git("ls-tree", "-r", "HEAD", "--name-only", timeout=30)
        return [
            line for line in output.strip().split("\n")
            if line.startswith("Mathlib/") and line.endswith(".lean")
        ]

    def get_file_content(self, filepath: str) -> str:
        """Get file content from bare repo."""
        return self._git("show", f"HEAD:{filepath}", timeout=30)

    def parse_declarations(self, filepath: str, content: str) -> list[dict]:
        """Parse a Lean 4 file for declarations."""
        lines = content.split("\n")
        declarations = []
        current_namespace = []
        last_docstring = None
        last_docstring_end = -1

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Track namespace
            if stripped.startswith("namespace "):
                ns = stripped[len("namespace "):].strip()
                current_namespace.append(ns)
                continue
            if stripped == "end" or stripped.startswith("end "):
                if current_namespace:
                    current_namespace.pop()
                continue

            # Capture docstrings
            if "/--" in stripped:
                # Find the full docstring (may span multiple lines)
                doc_text = []
                for j in range(i, min(i + 50, len(lines))):
                    doc_text.append(lines[j])
                    if "-/" in lines[j] and (j > i or lines[j].count("-/") > lines[j].count("/--")):
                        break
                full_doc = "\n".join(doc_text)
                match = DOCSTRING_RE.search(full_doc)
                if match:
                    last_docstring = match.group(1).strip()
                    last_docstring_end = j
                continue

            # Skip attributes, but note them
            if stripped.startswith("@["):
                # Check for @[simp] sub_self style (attribute-generated names)
                continue

            # Detect declarations
            for keyword in DECL_KEYWORDS:
                # Match: keyword name or keyword Name or protected keyword name
                prefix = ""
                check_line = stripped
                if check_line.startswith("protected "):
                    prefix = "protected "
                    check_line = check_line[len("protected "):]
                if check_line.startswith("noncomputable "):
                    check_line = check_line[len("noncomputable "):]
                if check_line.startswith("private "):
                    continue  # Skip private declarations

                if not check_line.startswith(keyword + " "):
                    continue

                rest = check_line[len(keyword) + 1:].strip()
                if not rest:
                    continue

                # Extract name (first non-space token, may contain dots)
                name_match = re.match(r"(\S+)", rest)
                if not name_match:
                    continue

                name = name_match.group(1)

                # Skip unnamed instances (instance : Foo)
                if name == ":" and keyword == "instance":
                    name = f"[anonymous_instance_{i}]"

                # Build full name with namespace
                if current_namespace and not any(name.startswith(ns + ".") for ns in current_namespace):
                    full_name = ".".join(current_namespace) + "." + name
                else:
                    full_name = name

                # Extract type signature (rest of line + continuation lines until := or where or by)
                sig_parts = [rest[len(name):].strip()]
                for j in range(i + 1, min(i + 20, len(lines))):
                    l = lines[j].strip()
                    if l.startswith(":=") or l.startswith("| ") or l == "where" or l.startswith("by"):
                        break
                    if any(l.startswith(kw + " ") for kw in DECL_KEYWORDS):
                        break
                    sig_parts.append(l)
                    if ":=" in l or " where" in l or " by" in l:
                        break

                type_sig = " ".join(sig_parts).strip()
                # Clean up: remove trailing := ... or by or where
                for sep in [":= by", ":=", " by", " where"]:
                    if sep in type_sig:
                        type_sig = type_sig[:type_sig.index(sep)].strip()

                # Use docstring if it was right before this declaration
                docstring = None
                if last_docstring and (i - last_docstring_end) <= 3:
                    docstring = last_docstring
                    last_docstring = None

                declarations.append({
                    "name": full_name,
                    "kind": keyword,
                    "filepath": filepath,
                    "line": i + 1,
                    "type_signature": type_sig if type_sig else None,
                    "docstring": docstring,
                    "is_public": "private" not in prefix,
                    "namespace": ".".join(current_namespace) if current_namespace else None,
                })
                break

        return declarations

    def extract_all(self):
        """Extract all declarations from Mathlib .lean files."""
        lean_files = self.list_lean_files()
        logger.info(f"Found {len(lean_files)} Lean files")

        total_decls = 0
        count = 0

        with self.session_factory() as session:
            for i, filepath in enumerate(lean_files):
                try:
                    content = self.get_file_content(filepath)
                except RuntimeError as e:
                    logger.warning(f"Failed to read {filepath}: {e}")
                    continue

                decls = self.parse_declarations(filepath, content)

                for d in decls:
                    existing = session.get(Declaration, d["name"])
                    if existing:
                        # Update
                        for key, val in d.items():
                            setattr(existing, key, val)
                    else:
                        session.add(Declaration(**d))
                        count += 1

                total_decls += len(decls)

                if (i + 1) % 500 == 0:
                    session.commit()
                    logger.info(f"  {i + 1}/{len(lean_files)} files, {total_decls} declarations")

            session.commit()

        logger.info(f"Extraction done: {total_decls} declarations from {len(lean_files)} files ({count} new)")
