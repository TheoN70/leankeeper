# Glossaire métier

Termes du domaine LeanKeeper / Mathlib. À enrichir au fil des découvertes.

| Terme | Définition | Alias/Contexte |
|-------|------------|----------------|
| Lean 4 | Assistant de preuve où compilation = correction | |
| Mathlib | Bibliothèque mathématique communautaire de Lean 4 (~2M lignes, ~210K théorèmes) | mathlib4 |
| Declaration | Théorème, définition, lemme, instance, classe ou structure Lean extrait du source | decl |
| Typeclass hierarchy | DAG des classes Mathlib (`Monoid → Group → Ring → Field`) | hiérarchie de typeclasses |
| Bors | Bot de merge utilisé par Mathlib ; PRs détectées via préfixe `[Merged by Bors]` | |
| RAG | Retrieval-Augmented Generation : récupération de contexte + génération LLM | |
| pgvector | Extension PostgreSQL pour stockage/recherche de vecteurs d'embeddings | |
| Embedding | Vecteur dense d'un texte, généré par sentence-transformers (`all-MiniLM-L6-v2`) | |
| Extractor | Classe extrayant une source de données (GitHub, Git, Zulip, Lean) vers PostgreSQL | |
| Review (PR) | Critère central du projet : « est-ce que ça passe la review Mathlib ? » (≠ « est-ce que ça compile ? ») | |
| Contributor mode / Reviewer mode | Deux modes du chat RAG (`prompt.py`) | |
| Zulip | Plateforme de discussion de la communauté Lean (décisions de design) | |
