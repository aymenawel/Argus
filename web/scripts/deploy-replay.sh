#!/usr/bin/env bash
# Deploy the public replay (D-83): this app built with NEXT_PUBLIC_ARGUS_REPLAY=1, with the bundles in public/bundles.
# The bundles are git-ignored and reach Vercel only in this upload, never in the repository. .vercelignore keeps
# secrets, node_modules and build folders out of it.
#
# Once, in your own terminal (from web/):  npx --yes vercel@64.5.0 login
#                                          npx --yes vercel@64.5.0 link --yes --project argus-replay
#                                          npx --yes vercel@64.5.0 git disconnect --yes
# Then from web/:                          bash scripts/deploy-replay.sh
#
# Vercel builds it (not `vercel build --prebuilt` here): a prebuilt output made on Windows links its functions with
# Windows symlinks that Vercel's Linux side can't follow, and copying them instead counts each copy as a function,
# past Hobby's 12 per deployment.
#
# The CLI is pinned to 64.5.0 (Oct 16, 2026) and run through npx, never added to package.json.
# Vercel Hobby takes at most 100 MB per CLI deploy (vercel.com/docs/limits); the source needs room too, so the
# bundles get 70 MB of it.
set -euo pipefail
cd "$(dirname "$0")/.."

VERCEL=(npx --yes vercel@64.5.0)
LIMIT_MB=70

if [ ! -f public/bundles/index.json ]; then
  echo "No bundles: run \`uv run python -m argus export-bundle <run id>\` in worker/ first." >&2
  exit 1
fi
size_mb=$(du -sm public/bundles | cut -f1)
if [ "$size_mb" -gt "$LIMIT_MB" ]; then
  echo "The bundles are ${size_mb} MB, over the ${LIMIT_MB} MB this deploy allows: re-export with --max-frames lower." >&2
  exit 1
fi
echo "Bundles: ${size_mb} MB"

"${VERCEL[@]}" deploy --prod --yes --build-env NEXT_PUBLIC_ARGUS_REPLAY=1
