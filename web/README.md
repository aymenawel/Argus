# Argus web app

The Next.js interface for Argus. It never touches cameras or the database: everything comes from the
Python worker's API (`worker/`). See the design spec in `docs/superpowers/specs/`.

```bash
npm install
npm run dev        # http://localhost:3000, expects the worker at http://localhost:8000
npm run lint && npm run typecheck && npm run build
```

Design tokens live in `styles/tokens.css` (light, dark, and dark by system preference).
