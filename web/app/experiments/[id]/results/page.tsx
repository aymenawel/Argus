import type { Metadata } from "next";
import { Suspense } from "react";
import { ResultsScreen } from "./ResultsScreen";
import styles from "./page.module.css";

export const metadata: Metadata = { title: "Results · Argus" };

// The experiment id comes from the URL at request time, so the client screen sits in a Suspense boundary.
export default function ResultsPage() {
  return (
    <Suspense fallback={<div className={styles.placeholder} aria-busy="true" />}>
      <ResultsScreen />
    </Suspense>
  );
}
