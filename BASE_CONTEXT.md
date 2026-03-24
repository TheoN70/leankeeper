# LeanKeeper — Base Context for AI-Assisted Mathlib Contributions

This file synthesizes all Mathlib contribution guidelines, conventions, and lessons learned from evaluation into a single reference for AI systems reviewing or producing Mathlib code. It is designed to be included as context when reviewing PRs or generating contributions.

This document will be improved as the project evolves and more evaluation data is collected.

---

## 1. Core Principle

**A proof that compiles is not necessarily good.** Lean guarantees correctness, but Mathlib reviewers check *design quality*: naming, generality, API completeness, style, and integration with the library. The goal is code that passes human review, not just code that compiles.

---

## 2. Naming Conventions

### 2.1 Capitalization

| What | Style | Example |
|------|-------|---------|
| Theorems, lemmas (terms of `Prop`) | `snake_case` | `mul_comm`, `add_le_add_left` |
| Types, classes, structures | `UpperCamelCase` | `CommMonoid`, `TopologicalSpace` |
| Functions | Named like return type | `toFun` (returns a function type) |
| Other terms | `lowerCamelCase` | `instOrderBot` |
| UpperCamelCase in snake_case | `lowerCamelCase` | `neZero_iff` (for `NeZero`) |
| Acronyms | Grouped | `LE` not `L_E`, `ne` not `n_e` |

### 2.2 Symbol Dictionary

| Symbol | Name | Symbol | Name |
|--------|------|--------|------|
| `∨` | `or` | `∧` | `and` |
| `→` | `of` / `imp` | `↔` | `iff` |
| `¬` | `not` | `=` | `eq` (often omitted) |
| `≠` | `ne` | `∘` | `comp` |
| `+` | `add` | `*` | `mul` |
| `-` (unary) | `neg` | `-` (binary) | `sub` |
| `⁻¹` | `inv` | `/` | `div` |
| `•` | `smul` | `^` | `pow` |
| `∣` | `dvd` | `∑` | `sum` |
| `∏` | `prod` | `∈` | `mem` |
| `≤` | `le` / `ge` | `<` | `lt` / `gt` |
| `⊔` | `sup` | `⊓` | `inf` |
| `⊥` | `bot` | `⊤` | `top` |
| `∪` | `union` | `∩` | `inter` |

### 2.3 Name Structure

- **Conclusion first**, hypotheses with `_of_`: `C_of_A_of_B` for `A → B → C`
- **Hypotheses in order** they appear (not reverse)
- **Abbreviations**: `pos` = `zero_lt`, `neg` = `lt_zero`, `nonpos` = `le_zero`, `nonneg` = `zero_le`
- **Infix follows pattern**: `-a * -b` → `neg_mul_neg` (not `mul_neg_neg`)
- **Left/right** for variants: `add_le_add_left`, `le_of_mul_le_mul_right`

### 2.4 Structural Lemma Names

| Pattern | Name | Attribute |
|---------|------|-----------|
| `(∀ x, f x = g x) → f = g` | `.ext` | `@[ext]` |
| `f = g ↔ ∀ x, f x = g x` | `.ext_iff` | |
| `Function.Injective f` | `f_injective` | |
| `f x = f y ↔ x = y` | `f_inj` | `@[simp]` candidate |

### 2.5 Dot Notation

Use namespace dots for projection notation: `And.symm`, `Eq.trans`, `LE.trans`, `LT.trans_le`.

### 2.6 Axiomatic Names

`refl`, `irrefl`, `symm`, `trans`, `antisymm`, `asymm`, `congr`, `comm`, `assoc`, `left_comm`, `right_comm`, `inj`.

### 2.7 Predicates

- Most predicates as **prefixes**: `isClosed_Icc`, not `Icc_isClosed`
- **Exceptions** (as suffixes): `_injective`, `_surjective`, `_bijective`, `_monotone`, `_antitone`, `_strictMono`, `_strictAnti`

### 2.8 Variable Conventions

| Variable | Usage |
|----------|-------|
| `α`, `β`, `γ` | Generic types |
| `x`, `y`, `z` | Elements |
| `h`, `h₁` | Assumptions |
| `G` | Groups |
| `R` | Rings |
| `K`, `𝕜` | Fields |
| `E` | Vector spaces |
| `m`, `n`, `k` | Natural numbers |
| `i`, `j`, `k` | Integers |

---

## 3. Generality

**Use the weakest typeclass that makes the proof work.** This is one of the most common review comments.

| Too specific | Correct | Reason |
|-------------|---------|--------|
| `Field` | `CommRing` | Proof doesn't use division |
| `Ring` | `Semiring` | Proof doesn't use negation |
| `CommRing` | `Semiring` | Proof doesn't use commutativity or negation |
| `Fintype` | `Finite` | Computability not needed |
| `Group` | `Monoid` | Proof doesn't use inverses |
| `LinearOrder` | `PartialOrder` | Proof doesn't use totality |

The typeclass hierarchy (simplified):
```
Semigroup → Monoid → Group → Ring → CommRing → Field
                              ↓
              AddGroup → AddCommGroup → Module → VectorSpace

TopologicalSpace → UniformSpace → MetricSpace → NormedSpace
```

---

## 4. API Completeness

### 4.1 For a new structure `Foo`

- `Foo.ext` with `@[ext]` — extensionality
- `Foo.ext_iff` — biconditional extensionality
- `Foo.mk` — constructor
- Coercions to parent types
- Docstrings on all fields

### 4.2 For a new operation

- Interaction with existing operations (`map_comp`, `map_id`)
- `_comm`, `_assoc` if applicable
- `_zero`, `_one` for identity elements
- `_add`, `_mul` for distributivity
- `@[simp]` lemmas for normalization

### 4.3 Common attributes

| Attribute | When to use |
|-----------|-------------|
| `@[simp]` | Normalization lemmas, definitional unfoldings |
| `@[ext]` | Extensionality lemmas |
| `@[to_additive]` | Multiplicative lemma with additive analogue |
| `@[simps]` | Auto-generate projections for definitions |
| `@[norm_cast]` | Cast-related lemmas |
| `@[gcongr]` | Monotonicity lemmas for `gcongr` tactic |

---

## 5. Code Style

### 5.1 Formatting

- **Line length**: max 100 characters
- **Indentation**: 2 spaces for proof body, 4 spaces for multiline theorem statement continuation
- **`by`** at end of previous line (never on its own line)
- **Declarations** flush-left (not indented inside namespaces/sections)
- **Explicit types** for all arguments and return types
- **No empty lines** inside declarations
- **Spaces** around `:`, `:=`, and infix operators
- **`fun x ↦`** preferred over `fun x =>` and `λ`
- **`<|`** preferred over `$`

### 5.2 Tactic mode

- One tactic per line (short sequences on one line OK: `cases bla; clear h`)
- Focusing dot `·` not indented, contents indented
- Terminal `simp` should NOT be squeezed (not replaced by `simp?` output)
- Prefer `gcongr` over manual `mul_le_mul_of_nonneg_left`
- Prefer `positivity` for positivity goals
- Short proof OK on one line: `by simp [h]`

### 5.3 Instances

Use `where` syntax:
```lean
instance instOrderBot : OrderBot ℕ where
  bot := 0
  bot_le := Nat.zero_le
```

### 5.4 Hypotheses

Prefer left of colon over universal quantifiers:
```lean
-- Good
theorem foo (n : ℝ) (h : 1 < n) : 0 < n := by linarith

-- Avoid
theorem foo : ∀ (n : ℝ), 1 < n → 0 < n := fun n h ↦ by linarith
```

---

## 6. Documentation

### 6.1 Module docstring (required)

```lean
/-!
# Title

Summary of the file contents.

## Main results

- `theorem_name`: description
- `def_name`: description

## Notation

- `|_|`: description

## References

See [Author2024] for details.
-/
```

### 6.2 Declaration docstrings

- **Required** on every definition and major theorem
- **Not required** on small API lemmas that mirror existing patterns (e.g., `mulSingle_pow` when `mulSingle_mul` exists without docstring)
- Should convey **mathematical meaning**, allowed to lie slightly about implementation
- Use backticks for Lean names, `$ $` for LaTeX

### 6.3 Proof comments

Complex proofs should have interspersed comments explaining the strategy:
```lean
-- We first reduce to the case where x is positive
-- Then we apply the induction hypothesis
```

---

## 7. PR Conventions

### 7.1 Title format

```
<type>(<scope>): <subject>
```

Types: `feat`, `fix`, `doc`, `style`, `refactor`, `chore`, `perf`, `ci`

Subject: imperative present tense, no capitalization, no trailing dot.

### 7.2 PR size and scope

- **~200 lines max** — smaller PRs get reviewed faster
- **Focused scope** — one concept per PR
- **Minimal imports** — use `#min_imports` to verify
- **File length** — keep under ~1000 lines, split if needed

### 7.3 Dependencies

List in description: `- [ ] depends on: #XXXX`

---

## 8. What Reviewers Check (priority order)

1. **Style**: formatting, naming conventions, PR title/description
2. **Documentation**: docstrings, cross-references, proof sketches
3. **Location**: declarations in right files, no duplicates, minimal imports
4. **Improvements**: better tactics, simpler proofs, split long proofs
5. **Library integration**: sensible API, sufficient generality, fits design

---

## 9. Common Mistakes to Avoid

### 9.1 Do NOT flag these (learned from evaluation)

- **Missing docstrings on small API lemmas** that mirror existing undocumented patterns — reviewers rarely flag this
- **PR description formatting** — reviewers focus on code, not PR metadata
- **Speculative concerns** about things not in the diff (e.g., "what about the right dual?" when only the left dual is modified)
- **Hypothetical performance issues** without evidence
- **File organization suggestions** for small PRs — save for dedicated refactoring PRs

### 9.2 DO flag these (high value)

- **Wrong naming convention** — this is the most common and most automatable review comment
- **Over-specialized hypotheses** — using `Field` when `Semiring` suffices
- **Missing `@[simp]`/`@[ext]`/`@[to_additive]`** attributes
- **Proof typos** — wrong lemma name, copy-paste errors
- **Formatting violations** — indentation, line length, `by` placement

### 9.3 Be direct

Real Mathlib reviewers are direct and specific:
- **Good**: "Rename to `foo_comm` per naming conventions"
- **Bad**: "You might consider whether the name could potentially be improved"

When an issue is identified, recommend a clear action. Do not hedge. If unsure, don't mention it.

---

## 10. AI Usage Policy

- AI use must be **disclosed** in PR description
- Author must **understand and vouch** for all AI-generated code
- AI-written code currently fails Mathlib standards by a large margin (as of March 2026)
- LeanKeeper's role: transform valid-but-non-idiomatic proofs into review-quality contributions

---

## 11. Review Severity Levels

| Level | Examples | Action |
|-------|----------|--------|
| **Blocking** | Wrong naming, over-specialized hypotheses, missing key attributes, proof errors | Must fix before merge |
| **Should fix** | Style violations, missing docstrings on definitions, non-idiomatic tactics | Expected to fix, but not a dealbreaker |
| **Suggestion** | Could generalize further, file could be split, alternative proof strategy | Nice to have, reviewer won't insist |

Focus on blocking and should-fix issues. Mention suggestions only when clearly beneficial.
