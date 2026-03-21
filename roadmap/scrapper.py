import requests

# Exemple basique pour récupérer les PRs et leurs review comments
headers = {"Authorization": "token ghp_..."}

def fetch_pr_reviews(repo, pr_number):
    # La PR elle-même
    pr = requests.get(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}",
        headers=headers
    ).json()
    
    # Les commentaires de review (inline sur le code)
    reviews = requests.get(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments",
        headers=headers
    ).json()
    
    # Les commentaires généraux
    comments = requests.get(
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
        headers=headers
    ).json()
    
    return pr, reviews, comments

"""
# Ce qu'il faut extraire via l'API GitHub
Les PRs avec leurs descriptions, les review comments inline (le reviewer qui dit "ce lemme devrait être généralisé à CommMonoid"), les discussions dans les issues, les labels, et les résultats de CI. L'API GitHub REST et GraphQL permettent d'extraire tout ça. Mathlib a environ 20 000+ PRs mergées, c'est parfaitement faisable.

# Et le Zulip
Les discussions les plus riches sur les choix de design sont souvent sur le Zulip Lean, pas sur GitHub. La bonne nouvelle : l'archive est publique et structurée par topics. L'API Zulip permet aussi l'extraction.

# Le dataset complet serait donc 
Le dépôt Git (commits + diffs), les PRs GitHub (description, review comments, changements demandés, version initiale vs finale), les discussions Zulip (topics liés à des choix de design Mathlib), les résultats des linters et de la CI, et le graphe d'imports comme métadonnée structurelle.
Tout est public et extractible. C'est un projet d'ingénierie data de quelques semaines, pas de quelques mois. Et le résultat serait un dataset unique au monde pour entraîner un agent de formalisation mathématique de qualité bibliothèque.
"""
