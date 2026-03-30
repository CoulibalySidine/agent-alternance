"""
dashboard.py — Génération du dashboard HTML de suivi (v2)
==========================================================

VERSION 2 — Améliorations :
- Filtres interactifs (statut, entreprise, lieu, score)
- Tri dynamique (score, entreprise, date, statut)
- Barre de recherche
- Design repensé avec palette sombre et typographie soignée
- Stats enrichies (graphique de répartition)
- Tout en JavaScript côté client (pas de serveur)
"""

from pathlib import Path
from datetime import datetime
from .tracker import Candidature, ETATS, charger_suivi
import json

DASHBOARD_PATH = Path(__file__).parent / "dashboard.html"


def generer_dashboard(candidatures: list[Candidature] = None, chemin: Path = DASHBOARD_PATH):
    """
    Génère un fichier HTML de dashboard interactif.

    Les filtres et le tri fonctionnent en JavaScript pur côté client.
    Pas besoin de serveur — ouvre le fichier .html dans Chrome.
    """
    if candidatures is None:
        candidatures = charger_suivi()

    if not candidatures:
        print("❌ Aucune candidature à afficher")
        return

    # --- Préparer les données en JSON pour le JS ---
    data_js = []
    for c in candidatures:
        data_js.append({
            "offre_id": c.offre_id,
            "titre": c.titre,
            "entreprise": c.entreprise,
            "lieu": c.lieu,
            "score": c.score,
            "url": c.url,
            "etat": c.etat,
            "historique": c.historique,
            "notes": c.notes,
            "date_creation": c.date_creation,
            "date_relance": c.date_relance,
            "doit_relancer": c.doit_relancer(),
            "jours_depuis_envoi": c.jours_depuis_envoi(),
        })

    data_json = json.dumps(data_js, ensure_ascii=False)

    # --- Listes uniques pour les filtres ---
    entreprises = sorted(set(c.entreprise for c in candidatures))
    lieux = sorted(set(c.lieu for c in candidatures if c.lieu))

    entreprises_json = json.dumps(entreprises, ensure_ascii=False)
    lieux_json = json.dumps(lieux, ensure_ascii=False)

    # --- Générer le HTML ---
    html = _generer_html(data_json, entreprises_json, lieux_json)
    chemin.write_text(html, encoding="utf-8")
    print(f"📊 Dashboard généré : {chemin}")
    print(f"   Ouvre-le dans Chrome : {chemin.resolve()}")


def _generer_html(data_json: str, entreprises_json: str, lieux_json: str) -> str:
    """Génère le HTML complet du dashboard."""
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Alternance — Dashboard de suivi</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg:         #0e1117;
            --surface:    #161b22;
            --surface-2:  #1c2129;
            --border:     #2a3140;
            --text:       #e6edf3;
            --text-muted: #7d8590;
            --accent:     #58a6ff;
            --accent-dim: #1a3a5c;
            --green:      #3fb950;
            --green-dim:  rgba(63,185,80,0.12);
            --yellow:     #d29922;
            --yellow-dim: rgba(210,153,34,0.12);
            --red:        #f85149;
            --red-dim:    rgba(248,81,73,0.12);
            --purple:     #bc8cff;
            --purple-dim: rgba(188,140,255,0.12);
            --radius:     10px;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'DM Sans', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 32px 24px;
            min-height: 100vh;
        }}

        .container {{ max-width: 1100px; margin: 0 auto; }}

        /* ===== HEADER ===== */
        .header {{
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            margin-bottom: 28px;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .header h1 {{
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        .header h1 span {{ color: var(--accent); }}
        .header .timestamp {{
            font-size: 12px;
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
        }}

        /* ===== STATS ROW ===== */
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-bottom: 24px;
        }}
        .stat {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 14px 16px;
            text-align: center;
        }}
        .stat .num {{
            font-size: 26px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }}
        .stat .label {{
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-top: 2px;
        }}
        .stat.highlight {{ border-color: var(--accent); background: var(--accent-dim); }}

        /* ===== ALERTES RELANCE ===== */
        .alerts {{
            background: var(--yellow-dim);
            border: 1px solid rgba(210,153,34,0.3);
            border-radius: var(--radius);
            padding: 14px 18px;
            margin-bottom: 24px;
            display: none;
        }}
        .alerts.visible {{ display: block; }}
        .alerts h3 {{
            font-size: 13px;
            font-weight: 600;
            color: var(--yellow);
            margin-bottom: 8px;
        }}
        .alert-item {{
            font-size: 13px;
            padding: 3px 0;
            color: var(--text);
        }}
        .alert-item strong {{ color: var(--yellow); }}

        /* ===== TOOLBAR (search + filtres + tri) ===== */
        .toolbar {{
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .search-box {{
            flex: 1;
            min-width: 200px;
            position: relative;
        }}
        .search-box input {{
            width: 100%;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 9px 14px 9px 36px;
            color: var(--text);
            font-family: 'DM Sans', sans-serif;
            font-size: 13px;
            outline: none;
            transition: border-color 0.2s;
        }}
        .search-box input:focus {{ border-color: var(--accent); }}
        .search-box::before {{
            content: '🔍';
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 13px;
        }}

        .filter-group {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}

        select, .btn {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 8px 12px;
            color: var(--text);
            font-family: 'DM Sans', sans-serif;
            font-size: 12px;
            cursor: pointer;
            outline: none;
            transition: border-color 0.2s;
        }}
        select:focus, .btn:hover {{ border-color: var(--accent); }}
        select option {{ background: var(--surface); }}

        .btn-reset {{
            background: transparent;
            color: var(--text-muted);
            border: 1px dashed var(--border);
            font-size: 11px;
        }}
        .btn-reset:hover {{ color: var(--accent); border-color: var(--accent); }}

        /* ===== COUNT BAR ===== */
        .count-bar {{
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 10px;
            font-family: 'JetBrains Mono', monospace;
        }}

        /* ===== TABLE ===== */
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
        }}
        thead th {{
            text-align: left;
            padding: 12px 16px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: var(--text-muted);
            background: var(--surface-2);
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
            transition: color 0.15s;
        }}
        thead th:hover {{ color: var(--accent); }}
        thead th .sort-arrow {{ font-size: 10px; margin-left: 4px; opacity: 0.4; }}
        thead th.active .sort-arrow {{ opacity: 1; color: var(--accent); }}

        tbody tr {{
            cursor: pointer;
            transition: background 0.12s;
        }}
        tbody tr:hover {{ background: var(--surface-2); }}
        tbody td {{
            padding: 11px 16px;
            font-size: 13px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }}
        tbody tr:last-child td {{ border-bottom: none; }}

        /* Score badges */
        .score {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 12px;
            font-family: 'JetBrains Mono', monospace;
        }}
        .score-high {{ background: var(--green-dim); color: var(--green); }}
        .score-mid  {{ background: var(--yellow-dim); color: var(--yellow); }}
        .score-low  {{ background: var(--red-dim); color: var(--red); }}

        /* État badges */
        .etat {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            white-space: nowrap;
        }}
        .etat-brouillon    {{ background: rgba(125,133,144,0.15); color: var(--text-muted); }}
        .etat-envoyee      {{ background: var(--accent-dim); color: var(--accent); }}
        .etat-vue          {{ background: var(--purple-dim); color: var(--purple); }}
        .etat-entretien    {{ background: var(--yellow-dim); color: var(--yellow); }}
        .etat-acceptee     {{ background: var(--green-dim); color: var(--green); font-weight: 600; }}
        .etat-refusee      {{ background: var(--red-dim); color: var(--red); }}
        .etat-sans_reponse {{ background: rgba(125,133,144,0.10); color: var(--text-muted); }}

        .badge-relance {{
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            background: var(--red-dim);
            color: var(--red);
            margin-left: 6px;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.5; }} }}

        .sub {{ color: var(--text-muted); font-size: 12px; }}
        .jours {{ font-family: 'JetBrains Mono', monospace; color: var(--text-muted); font-size: 12px; }}

        /* ===== DETAIL ROW ===== */
        .detail-row {{ display: none; }}
        .detail-row.open {{ display: table-row; }}
        .detail-row td {{ padding: 0 !important; border-bottom: 1px solid var(--border) !important; }}
        .detail-content {{
            background: var(--bg);
            padding: 16px 24px;
            display: grid;
            grid-template-columns: 1fr 1fr auto;
            gap: 20px;
            font-size: 13px;
        }}
        .detail-section h4 {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 6px;
        }}
        .detail-section ul {{ list-style: none; }}
        .detail-section li {{
            padding: 3px 0;
            color: var(--text-muted);
            font-size: 12px;
        }}
        .detail-section li::before {{
            content: '›';
            color: var(--accent);
            margin-right: 6px;
        }}
        .detail-section a {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
            font-size: 13px;
        }}
        .detail-section a:hover {{ text-decoration: underline; }}

        /* ===== EMPTY STATE ===== */
        .empty-state {{
            text-align: center;
            padding: 48px;
            color: var(--text-muted);
            font-size: 14px;
            display: none;
        }}
        .empty-state.visible {{ display: block; }}

        /* ===== FOOTER ===== */
        .footer {{
            text-align: center;
            margin-top: 40px;
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 0.3px;
            font-family: 'JetBrains Mono', monospace;
        }}

        /* ===== RESPONSIVE ===== */
        @media (max-width: 768px) {{
            body {{ padding: 16px 12px; }}
            .toolbar {{ flex-direction: column; }}
            .search-box {{ min-width: 100%; }}
            .detail-content {{ grid-template-columns: 1fr; }}
            table {{ font-size: 12px; }}
        }}
    </style>
</head>
<body>
<div class="container">

    <div class="header">
        <h1><span>⚡</span> Agent Alternance — Suivi</h1>
        <span class="timestamp">maj {now}</span>
    </div>

    <!-- Stats -->
    <div class="stats" id="stats"></div>

    <!-- Alertes relance -->
    <div class="alerts" id="alerts">
        <h3 id="alerts-title"></h3>
        <div id="alerts-list"></div>
    </div>

    <!-- Toolbar : recherche + filtres + tri -->
    <div class="toolbar">
        <div class="search-box">
            <input type="text" id="search" placeholder="Rechercher (poste, entreprise, lieu…)" />
        </div>
        <div class="filter-group">
            <select id="filter-etat">
                <option value="">Tous les statuts</option>
                <option value="brouillon">📝 Brouillon</option>
                <option value="envoyee">📤 Envoyée</option>
                <option value="vue">👁️ Vue</option>
                <option value="entretien">🎤 Entretien</option>
                <option value="acceptee">✅ Acceptée</option>
                <option value="refusee">❌ Refusée</option>
                <option value="sans_reponse">⏳ Sans réponse</option>
            </select>
            <select id="filter-entreprise">
                <option value="">Toutes les entreprises</option>
            </select>
            <select id="filter-lieu">
                <option value="">Tous les lieux</option>
            </select>
            <select id="filter-score">
                <option value="">Tous les scores</option>
                <option value="70-100">≥ 70 (élevé)</option>
                <option value="40-69">40–69 (moyen)</option>
                <option value="0-39">< 40 (faible)</option>
                <option value="none">Non scoré</option>
            </select>
            <select id="sort-by">
                <option value="score-desc">Tri : Score ↓</option>
                <option value="score-asc">Tri : Score ↑</option>
                <option value="entreprise-asc">Tri : Entreprise A-Z</option>
                <option value="entreprise-desc">Tri : Entreprise Z-A</option>
                <option value="date-desc">Tri : Plus récent</option>
                <option value="date-asc">Tri : Plus ancien</option>
                <option value="etat-asc">Tri : Statut</option>
            </select>
            <button class="btn btn-reset" onclick="resetFilters()">✕ Réinitialiser</button>
        </div>
    </div>

    <div class="count-bar" id="count-bar"></div>

    <!-- Table -->
    <table>
        <thead>
            <tr>
                <th style="width:65px">Score</th>
                <th>Poste</th>
                <th>Lieu</th>
                <th>État</th>
                <th style="width:60px">Jours</th>
            </tr>
        </thead>
        <tbody id="tbody"></tbody>
    </table>

    <div class="empty-state" id="empty-state">
        Aucune candidature ne correspond aux filtres sélectionnés.
    </div>

    <div class="footer">
        Agent IA Alternance · Sidiné COULIBALY · Sourcing → Qualification → Candidature → Suivi
    </div>
</div>

<script>
// ===== DATA =====
const CANDIDATURES = {data_json};
const ENTREPRISES = {entreprises_json};
const LIEUX = {lieux_json};
const ETATS = {{
    "brouillon":"📝","envoyee":"📤","vue":"👁️",
    "entretien":"🎤","acceptee":"✅","refusee":"❌","sans_reponse":"⏳"
}};
const ETAT_ORDER = ["brouillon","envoyee","vue","entretien","acceptee","refusee","sans_reponse"];

// ===== INIT FILTER OPTIONS =====
function initFilters() {{
    const selEnt = document.getElementById('filter-entreprise');
    ENTREPRISES.forEach(e => {{
        const opt = document.createElement('option');
        opt.value = e; opt.textContent = e;
        selEnt.appendChild(opt);
    }});
    const selLieu = document.getElementById('filter-lieu');
    LIEUX.forEach(l => {{
        const opt = document.createElement('option');
        opt.value = l; opt.textContent = l;
        selLieu.appendChild(opt);
    }});
}}

// ===== STATS =====
function renderStats(data) {{
    const total = data.length;
    const parEtat = {{}};
    data.forEach(c => parEtat[c.etat] = (parEtat[c.etat]||0) + 1);
    const scores = data.filter(c => c.score != null).map(c => c.score);
    const scoreMoyen = scores.length ? (scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(0) : '—';

    let html = `<div class="stat highlight"><div class="num">${{total}}</div><div class="label">Total</div></div>`;
    html += `<div class="stat"><div class="num">${{scoreMoyen}}</div><div class="label">Score moyen</div></div>`;
    ETAT_ORDER.forEach(etat => {{
        const count = parEtat[etat] || 0;
        if (count > 0) {{
            html += `<div class="stat"><div class="num">${{ETATS[etat]}} ${{count}}</div><div class="label">${{etat.replace('_',' ')}}</div></div>`;
        }}
    }});
    document.getElementById('stats').innerHTML = html;
}}

// ===== ALERTES =====
function renderAlerts(data) {{
    const relances = data.filter(c => c.doit_relancer);
    const box = document.getElementById('alerts');
    if (relances.length === 0) {{ box.classList.remove('visible'); return; }}
    box.classList.add('visible');
    document.getElementById('alerts-title').textContent = `🔔 ${{relances.length}} candidature${{relances.length>1?'s':''}} à relancer`;
    document.getElementById('alerts-list').innerHTML = relances.map(c =>
        `<div class="alert-item">${{ETATS[c.etat]||'❓'}} <strong>${{c.entreprise}}</strong> — ${{c.titre}}</div>`
    ).join('');
}}

// ===== TABLE =====
function renderTable(data) {{
    const tbody = document.getElementById('tbody');
    if (data.length === 0) {{
        tbody.innerHTML = '';
        document.getElementById('empty-state').classList.add('visible');
        return;
    }}
    document.getElementById('empty-state').classList.remove('visible');

    tbody.innerHTML = data.map(c => {{
        const scoreClass = (c.score||0) >= 70 ? 'score-high' : (c.score||0) >= 40 ? 'score-mid' : 'score-low';
        const scoreVal = c.score != null ? c.score : '—';
        const relBadge = c.doit_relancer ? '<span class="badge-relance">RELANCER</span>' : '';
        const jours = c.jours_depuis_envoi != null ? `J+${{c.jours_depuis_envoi}}` : '—';
        const derniereNote = c.notes.length ? c.notes[c.notes.length-1].texte : '—';
        const histHtml = c.historique.map(h =>
            `<li>${{h.date.slice(0,10)}} — ${{h.etat}} : ${{h.commentaire||''}}</li>`
        ).join('');

        return `
            <tr onclick="toggleDetail('${{c.offre_id}}')">
                <td><span class="score ${{scoreClass}}">${{scoreVal}}</span></td>
                <td><strong>${{c.titre}}</strong><br><span class="sub">${{c.entreprise}}</span></td>
                <td>${{c.lieu}}</td>
                <td><span class="etat etat-${{c.etat}}">${{ETATS[c.etat]||'❓'}} ${{c.etat.replace('_',' ')}}</span>${{relBadge}}</td>
                <td><span class="jours">${{jours}}</span></td>
            </tr>
            <tr class="detail-row" id="detail-${{c.offre_id}}">
                <td colspan="5">
                    <div class="detail-content">
                        <div class="detail-section">
                            <h4>Historique</h4>
                            <ul>${{histHtml}}</ul>
                        </div>
                        <div class="detail-section">
                            <h4>Notes</h4>
                            <p style="color:var(--text-muted)">${{derniereNote}}</p>
                        </div>
                        <div class="detail-section">
                            <h4>Offre</h4>
                            <a href="${{c.url}}" target="_blank">Voir l'offre ↗</a>
                        </div>
                    </div>
                </td>
            </tr>`;
    }}).join('');
}}

// ===== TOGGLE DETAIL =====
function toggleDetail(id) {{
    const row = document.getElementById('detail-' + id);
    row.classList.toggle('open');
}}

// ===== FILTRAGE & TRI =====
function getFiltered() {{
    const search = document.getElementById('search').value.toLowerCase();
    const etat = document.getElementById('filter-etat').value;
    const entreprise = document.getElementById('filter-entreprise').value;
    const lieu = document.getElementById('filter-lieu').value;
    const scoreFilt = document.getElementById('filter-score').value;
    const sortBy = document.getElementById('sort-by').value;

    let data = CANDIDATURES.filter(c => {{
        if (search && !(
            c.titre.toLowerCase().includes(search) ||
            c.entreprise.toLowerCase().includes(search) ||
            c.lieu.toLowerCase().includes(search)
        )) return false;
        if (etat && c.etat !== etat) return false;
        if (entreprise && c.entreprise !== entreprise) return false;
        if (lieu && c.lieu !== lieu) return false;
        if (scoreFilt) {{
            if (scoreFilt === 'none') {{ if (c.score != null) return false; }}
            else {{
                const [min, max] = scoreFilt.split('-').map(Number);
                if (c.score == null || c.score < min || c.score > max) return false;
            }}
        }}
        return true;
    }});

    // Tri
    const [field, dir] = sortBy.split('-');
    data.sort((a, b) => {{
        let va, vb;
        if (field === 'score') {{
            va = a.score ?? -1; vb = b.score ?? -1;
        }} else if (field === 'entreprise') {{
            va = a.entreprise.toLowerCase(); vb = b.entreprise.toLowerCase();
        }} else if (field === 'date') {{
            va = a.date_creation; vb = b.date_creation;
        }} else if (field === 'etat') {{
            va = ETAT_ORDER.indexOf(a.etat); vb = ETAT_ORDER.indexOf(b.etat);
        }}
        if (va < vb) return dir === 'asc' ? -1 : 1;
        if (va > vb) return dir === 'asc' ? 1 : -1;
        return 0;
    }});

    return data;
}}

function refresh() {{
    const data = getFiltered();
    renderStats(data);
    renderAlerts(data);
    renderTable(data);
    document.getElementById('count-bar').textContent =
        `${{data.length}} / ${{CANDIDATURES.length}} candidature${{data.length > 1 ? 's' : ''}} affichée${{data.length > 1 ? 's' : ''}}`;
}}

function resetFilters() {{
    document.getElementById('search').value = '';
    document.getElementById('filter-etat').value = '';
    document.getElementById('filter-entreprise').value = '';
    document.getElementById('filter-lieu').value = '';
    document.getElementById('filter-score').value = '';
    document.getElementById('sort-by').value = 'score-desc';
    refresh();
}}

// ===== EVENT LISTENERS =====
document.getElementById('search').addEventListener('input', refresh);
document.getElementById('filter-etat').addEventListener('change', refresh);
document.getElementById('filter-entreprise').addEventListener('change', refresh);
document.getElementById('filter-lieu').addEventListener('change', refresh);
document.getElementById('filter-score').addEventListener('change', refresh);
document.getElementById('sort-by').addEventListener('change', refresh);

// ===== INIT =====
initFilters();
refresh();
</script>
</body>
</html>"""
