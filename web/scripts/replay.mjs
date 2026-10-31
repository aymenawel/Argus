// `npm run replay`: the app in replay mode (D-83) on port 3001, beside the normal dev server on 3000. It builds into
// .next-replay so the two never share a build folder.
import { spawn } from "node:child_process";

const env = { ...process.env, NEXT_PUBLIC_ARGUS_REPLAY: "1", ARGUS_DIST_DIR: ".next-replay" };
const child = spawn("npx", ["next", "dev", "-p", "3001"], {
  env,
  stdio: "inherit",
  shell: process.platform === "win32",
});
child.on("exit", (code) => process.exit(code ?? 0));
