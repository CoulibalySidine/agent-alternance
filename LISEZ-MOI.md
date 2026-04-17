# Agent Alternance — Guide d'installation

## Prérequis

Aucun ! Tout est inclus dans l'application.

## Installation

1. **Décompresse** le dossier `AgentAlternance` où tu veux sur ton PC
2. **Crée un fichier `.env`** dans le dossier `AgentAlternance` avec ce contenu :

```
ANTHROPIC_API_KEY=sk-ant-ta-cle-ici
```

> Pour obtenir une clé API :
> - Va sur https://console.anthropic.com
> - Crée un compte gratuit
> - Génère une clé API dans les paramètres

3. **Double-clique** sur `AgentAlternance.exe`

## Versions disponibles

**Release Web** — L'appli s'ouvre dans ton navigateur (Chrome, Firefox, Edge...).
Une petite fenêtre console reste ouverte : c'est le serveur, ne la ferme pas tant que tu utilises l'appli.

**Release App** — L'appli s'ouvre dans sa propre fenêtre, sans navigateur.
Rien d'autre ne s'affiche à l'écran.

## Utilisation

1. **Upload ton CV** (PDF ou Word) sur la page d'accueil
2. **Vérifie ton profil** dans l'éditeur visuel (corrige si besoin)
3. **Lance un scraping** pour collecter des offres d'alternance
4. **Score les offres** avec l'IA pour voir lesquelles te correspondent
5. **Génère tes candidatures** (lettre de motivation, CV adapté, fiche entretien)
6. **Suis tes candidatures** dans le tableau kanban (glisse-dépose entre colonnes)

## En cas de problème

- **"Windows a protégé votre PC"** : Clique sur "Informations complémentaires" puis "Exécuter quand même". C'est normal pour les applications non signées.
- **L'appli ne se lance pas** : Vérifie que le fichier `.env` existe et contient ta clé API.
- **Erreur de connexion** : Vérifie ta connexion internet (nécessaire pour le scraping et l'IA).
- **Release App ne marche pas** : Utilise la Release Web à la place, elle est plus compatible.

## Crédits

Développé par Sidiné COULIBALY
https://github.com/CoulibalySidine/agent-alternance
