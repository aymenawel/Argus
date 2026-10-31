import { type NextRequest, NextResponse } from "next/server";
import { isReplay, isReplayPath } from "./lib/replay.ts";

// The public replay (D-83) is this app built with NEXT_PUBLIC_ARGUS_REPLAY=1: every path outside /replay, its
// bundles and the app's assets goes to /replay. Outside replay mode nothing is changed.
export function proxy(request: NextRequest) {
  if (!isReplay() || isReplayPath(request.nextUrl.pathname)) return NextResponse.next();
  return NextResponse.redirect(new URL("/replay", request.url));
}
