"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ResultsScreen } from "@/app/experiments/[id]/results/ResultsScreen";
import { RunScreen } from "@/app/experiments/[id]/run/RunScreen";
import { ReplayBanner } from "@/components/replay/ReplayBanner";
import { PageHeader } from "@/components/shell/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { type BundleManifest, openBundle } from "@/lib/replay";
import styles from "../page.module.css";

type Opened = { runId: string; manifest?: BundleManifest; error?: string };

// One bundled run (D-83): its manifest first (which experiment, how its frames were thinned), then the app's own
// Run view or Results reading from the bundle.
export function ReplayRun({ view }: { view: "run" | "results" }) {
  const { runId } = useParams<{ runId: string }>();
  const [opened, setOpened] = useState<Opened | null>(null);

  useEffect(() => {
    let live = true;
    openBundle(runId)
      .then((manifest) => live && setOpened({ runId, manifest }))
      .catch((e: unknown) => live && setOpened({ runId, error: e instanceof Error ? e.message : String(e) }));
    return () => {
      live = false;
    };
  }, [runId]);

  const current = opened?.runId === runId ? opened : null;
  if (current?.manifest) {
    const { manifest } = current;
    return (
      <>
        <ReplayBanner manifest={manifest} />
        {view === "run" ? (
          <RunScreen key={manifest.run_id} experimentId={manifest.experiment_id} />
        ) : (
          <ResultsScreen key={manifest.run_id} experimentId={manifest.experiment_id} />
        )}
      </>
    );
  }
  return (
    <>
      <ReplayBanner manifest={null} />
      {current?.error ? (
        <>
          <PageHeader crumb={<Link href="/replay">Replays</Link>} title="Replay" />
          <Panel className={styles.panel}>
            <div className={styles.message} role="alert">
              <p className={styles.messageTitle}>The replay couldn&apos;t load: {current.error}.</p>
            </div>
          </Panel>
        </>
      ) : (
        <div className={styles.placeholder} aria-busy="true" />
      )}
    </>
  );
}
