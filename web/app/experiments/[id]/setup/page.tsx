import type { Metadata } from "next";
import { Suspense } from "react";
import { SetupScreen } from "./SetupScreen";
import styles from "./page.module.css";

export const metadata: Metadata = { title: "Setup · Argus" };

// The experiment id comes from the URL at request time, so the client screen sits in a Suspense boundary.
export default function SetupPage() {
  return (
    <Suspense fallback={<div className={styles.placeholder} aria-busy="true" />}>
      <SetupScreen />
    </Suspense>
  );
}
