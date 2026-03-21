# LeanKeeper — A native AI agent for Mathlib

## Vision

Build a specialized AI agent, trained specifically on the conventions, hierarchy and culture of [Mathlib](https://github.com/leanprover-community/mathlib4), capable of producing library-quality contributions — not just proofs that compile, but code that passes human review.

## Context

### Lean and Mathlib

- **Lean** is a proof assistant and programming language developed by Leonardo de Moura (Lean FRO). If it compiles, the proof is correct.
- **Mathlib** is the community library of formalized mathematics in Lean 4: ~210,000 theorems, ~100,000 definitions, ~2 million lines of code, 500+ contributors over 8 years.
- Mathlib is organized as a **dependency DAG** with a **typeclass hierarchy** (`Monoid → Group → Ring → Field`, `TopologicalSpace → MetricSpace → NormedSpace`...) enabling automatic proof reuse.

### AI and theorem proving

| Project | Organization | Key result |
|---------|-------------|------------|
| **AlphaProof** | Google DeepMind | IMO 2024 silver medal, gold in 2025 |
| **Aristotle** | xAI | IMO 2025 gold medal (Lean formal verification) |
| **Goedel-Prover-V2** | Princeton | Most powerful open-source prover, 90% on miniF2F |
| **Gauss** | Math, Inc. | Formalization of the strong PNT in 3 weeks |
| **HyperTree Proof Search** | Meta | 10 IMO problems solved |

All converge on the same architecture: **LLM for intuition + Lean for formal verification**.

## The problem: current AI harms Mathlib

### Massive dumps, not contributions

AI companies produce Lean code that **compiles** but is **not Mathlib quality**: definitions at the wrong level of generality, naming conventions not respected, no API, unmaintainable code, submitted in monolithic blocks impossible to review.

### Concrete consequences (Zulip discussion, March 2026)

- **Sebastien Gouezel** (maintainer): *"If Math, Inc. formalizes Mazur's theorem in a crappy way, nobody will want to redo it properly, and we'll never have Mazur in Mathlib."*
- **Patrick Massot** (blueprint system creator): *"AI companies are going to bombard this area and turn it into a radioactive wasteland."*
- Master's students lost their thesis topic after Gauss scooped the sphere packing result.

### The fundamental problem: definitions

**A proof that compiles is not necessarily "good."** Definitions can be at the wrong level of generality, poorly integrated into the typeclass hierarchy, without standard API, or semantically wrong — and Lean won't warn you. This design judgment is what current AI cannot do.

## The proposition: LeanKeeper

### Why it's feasible

- Mathlib is ~2M lines (~50-70M tokens) — trivial fine-tuning for current models.
- Conventions are a **closed corpus**, well documented: naming, style, hierarchy, API patterns.
- Automated linters already encode some of the rules.
- PR reviews are public: ~20,000+ merged PRs on GitHub with comments.

### The training dataset

| Source | Content | Value |
|--------|---------|-------|
| Git repository | Commits, diffs | The *what* (final code) |
| GitHub PRs | Initial version → comments → final version | The *why* (design judgment) |
| Lean Zulip | Discussions on definition choices | The *reasoning* behind decisions |
| Linters / CI | Automated results | The formalized *rules* |
| Import graph | Structured dependency graph | The *topology* of the library |

Everything is public and extractable via GitHub and Zulip APIs.

### What LeanKeeper would do

The agent works like a **good junior Mathlib contributor**:

1. **Receives** a theorem to formalize (in natural or informal language).
2. **Explores** the existing typeclass hierarchy to find the right level of generality.
3. **Proposes** a definition integrated into the hierarchy, with standard API.
4. **Writes** the proof with the right tactics and style.
5. **Checks** naming against Mathlib conventions.
6. **Submits** a clean, focused PR (~200 lines), ready for review.

### Success metric

Not "does it compile" (trivial) but **"does it pass Mathlib review"** — maintainers accept to merge without major modifications.

## Mathlib's bottleneck

- **~300 PRs pending**, median delay ~2 weeks.
- Reviewers check **design**, not correctness (Lean handles that).
- Reviewers are mostly volunteers, with rare profiles (expert in the mathematical domain AND in Lean/Mathlib).
- Recent funding: **$10M from Alex Gerko** (XTX Markets) — $5M to Lean FRO, $5M to the Mathlib Initiative.


## Documentation

- **[Project wiki](https://github.com/TheoN70/leankeeper/wiki)** — Quickstart, architecture, data sources, conventions, roadmap
- **[`leankeeper/README.md`](leankeeper/README.md)** — Package-level setup and usage
- **[`DB_ARCHITECTURE.md`](DB_ARCHITECTURE.md)** — Full database schema

## References

- [Mathlib GitHub](https://github.com/leanprover-community/mathlib4)
- [Mathlib Initiative](https://mathlib-initiative.org/)
- [Lean FRO](https://lean-lang.org/fro/)
- [Zulip discussion: "The role of AI companies in large formalisation projects"](https://leanprover.zulipchat.com/#narrow/channel/113488-general/topic/The.20role.20of.20AI.20companies.20in.20large.20formalisation.20projects)
- [Kevin Buzzard — Xena Project](https://xenaproject.wordpress.com/)
- [AlphaProof (Nature, Nov. 2025)](https://www.nature.com/articles/s41586-025-09833-y)
- [Aristotle (xAI)](https://arxiv.org/html/2510.01346v1)
- [Gauss (Math, Inc.)](https://www.math.inc/gauss)
- [Goedel-Prover-V2 (Princeton)](https://ai.princeton.edu/news/2025/princeton-researchers-unveil-improved-mathematical-theorem-prover-powered-ai)
- [Growing Mathlib (arXiv)](https://arxiv.org/html/2508.21593v2)
