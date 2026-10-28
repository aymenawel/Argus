import type { Metadata } from "next";
import { Suspense } from "react";
import { RunScreen } from "./RunScreen";
import styles from "./page.module.css";

export const metadata: Metadata = { title: "Run · Argus" };

// The run id comes from the URL at request time, so the client screen sits in a Suspense boundary.
export default function RunPage() {
  return (
    <Suspense fallback={<div className={styles.placeholder} aria-busy="true" />}>
      <RunScreen />
    </Suspense>
  );
}
