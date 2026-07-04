# SmartPlay AI — interface React

Application minimale (Vite + React) pour envoyer une vidéo à l’API FastAPI, suivre le statut du job et afficher le JSON de résultats.

## Prérequis

- Node.js 18+
- Backend lancé : depuis la racine du dépôt Python  

  `uvicorn api_server:app --reload --host 0.0.0.0 --port 8000`

- Keypoints du terrain : **calibrage dans le navigateur** (bouton « Charger la 1ère image », puis 12 clics), **ou** JSON / fichier `.json`, **ou** fichier serveur `cache/fixed_keypoints_detection.json` (voir `python main.py` / `manual_keypoints_selection.py`).

## Installation

```bash
cd padel-ui
npm install
```

## Développement

```bash
npm run dev
```

Ouvre `http://localhost:5173`. La variable `VITE_API_URL` dans `.env.development` pointe par défaut vers `http://localhost:8000`.

Pour tester depuis un téléphone sur le même réseau :

1. Lancer l’API avec `--host 0.0.0.0`.
2. Lancer Vite avec `npm run dev` (le `vite.config.js` expose déjà `host: true`).
3. Mettre dans `.env.development` l’URL du PC : `VITE_API_URL=http://192.168.x.x:8000`.
4. Accéder au front depuis le téléphone via l’IP du PC et le port affiché par Vite (souvent 5173).

## API (`POST /jobs`)

Multipart :

- `file` — vidéo (obligatoire).
- `court_keypoints_json` — chaîne JSON optionnelle : tableau de 12 paires `[x, y]` en coordonnées pixels de la vidéo.
- `keypoints_file` — fichier JSON optionnel (même format) ; prioritaire sur `court_keypoints_json` si les deux sont envoyés.

Si aucun keypoint n’est fourni dans la requête, l’API utilise `cache/fixed_keypoints_detection.json` s’il existe.

### `GET /jobs/{job_id}/analytics`

À appeler une fois le job **completed**. Retourne cartes joueurs (distance, vitesses, frappes), série temporelle pour graphique vitesse, positions échantillonnées pour carte terrain, répartition des types de coups — même logique que `dashboard.py` / `data.csv`.

### `POST /tools/first-frame`

Multipart : `file` (vidéo). Réponse JSON : `width`, `height`, `mime`, `image_base64` (JPEG de la première frame). Utilisé par l’UI React pour calibrer les 12 points au clic.

## Production (optionnel)

```bash
npm run build
```

Les fichiers statiques sont dans `dist/`. Vous pouvez les servir via nginx ou les monter depuis FastAPI (`StaticFiles`).

## Variables d’environnement

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Origine de l’API (sans slash final), ex. `http://localhost:8000` |

Côté API, `FRONTEND_ORIGINS` (liste séparée par des virgules) contrôle le CORS, par défaut les origines Vite locales.
