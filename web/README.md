# Argus web app

The Next.js interface for Argus. It never touches cameras or the database: everything comes from the
Python worker's API (`worker/`). See the design spec in `docs/superpowers/specs/`.

Start the worker and this app together, from `worker/` (needs a `.env` in the repo root; copy `.env.example`):

```bash
uv run python -m argus dev   # worker on http://localhost:8000, web app on http://localhost:3000
```

Or this app on its own, from `web/`:

```bash
npm install
npm run dev        # http://localhost:3000, expects the worker at NEXT_PUBLIC_ARGUS_API or http://localhost:8000
npm run lint && npm run typecheck && npm run build
```

Design tokens live in `styles/tokens.css` (light, dark, and dark by system preference). `/kit` shows every shared
component in every state.
