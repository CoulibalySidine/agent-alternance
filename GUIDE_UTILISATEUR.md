# 🤖 Agent Alternance — Guide d'utilisation

## Première fois : Installation

1. **Installe Python** → https://www.python.org/downloads/
   - ⚠️ Coche **"Add Python to PATH"** pendant l'installation
   
2. **Installe Node.js** → https://nodejs.org/ (bouton vert "LTS")

3. **Double-clic sur `INSTALLER.bat`**
   - Ça installe tout automatiquement
   - À la fin, ça ouvre le fichier `.env` — colle ta clé API dedans

4. **Clé API Anthropic** :
   - Va sur https://console.anthropic.com
   - Crée un compte
   - Va dans "API Keys" → "Create Key"
   - Copie la clé (commence par `sk-ant-...`)
   - Colle-la dans le fichier `.env` à la place de `sk-ant-ta-cle-ici`
   - Sauvegarde et ferme

## À chaque utilisation

**Double-clic sur `LANCER.bat`** — ça ouvre tout automatiquement.

Le navigateur s'ouvre sur l'application. Si ça ne s'ouvre pas, va sur http://localhost:5173

## Utiliser l'application

### Étape 1 — Profil (page d'accueil)

1. Glisse ton CV (PDF ou Word) dans la zone
2. Tape le poste que tu cherches (ex: "data analyst", "développeur web")
3. Tape la ville (ex: "Lyon", "Paris")
4. Clic **"Analyser mon CV"**
5. Attends ~10 secondes → ton profil apparaît
6. Vérifie que les infos sont correctes → clic "Modifier" si besoin

### Étape 2 — Offres (menu à gauche)

1. Clic **"Scraper des offres"** → une fenêtre s'ouvre
2. Les mots-clés et la ville sont pré-remplis, modifie si besoin
3. Clic **"Lancer"** → les offres apparaissent
4. Clic **"Scorer (5 offres)"** → l'IA évalue chaque offre pour toi
5. Score **vert (70+)** = bon match, **jaune (40-69)** = moyen, **rouge (<40)** = pas pour toi

### Étape 3 — Actions sur une offre

- 🎯 = Scorer cette offre individuellement
- 📁 = Générer le dossier de candidature (CV adapté + lettre + fiche entretien)
- 📌 = Ajouter au suivi
- Clic sur la ligne = voir le détail + l'analyse IA

### Étape 4 — Suivi (menu à gauche)

- Voir toutes tes candidatures
- Changer l'état : Brouillon → Envoyée → Entretien → Acceptée
- Les candidatures à relancer sont signalées en rouge 🔔

## Coût

L'application utilise l'IA Claude (payant). Chaque session coûte environ **0.30 à 0.70€**. 
Avec 5€ de crédit, tu peux faire environ 10 sessions complètes.

## Problèmes courants

| Problème | Solution |
|----------|----------|
| "API hors ligne" dans la sidebar | Vérifie que LANCER.bat est bien lancé |
| "Clé API non configurée" | Ouvre `.env` et vérifie que ta clé est bien collée |
| Aucune offre trouvée | Change les mots-clés dans le scraping |
| Score = "—" | Clic sur 🎯 pour scorer l'offre |

## Pour arrêter

Ferme la fenêtre noire `LANCER.bat` — tout s'arrête.
