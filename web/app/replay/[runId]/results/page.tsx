import type { Metadata } from "next";
import { Suspense } from "react";
import { ReplayRun } from "../ReplayRun";
import styles from "../../page.module.css";

export const metadata: Metadata = { title: "Replay · Argus" };

// The run id comes from the URL at request time, so the client screen sits in a Suspense boundary.
export default function ReplayResultsPage() {
  return (
    <Suspense fallback={<div className={styles.placeholder} aria-busy="true" />}>
      <ReplayRun view="results" />
    </Suspense>
  );
}
