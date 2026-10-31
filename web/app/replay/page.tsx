import type { Metadata } from "next";
import { Suspense } from "react";
import { ReplayIndex } from "./ReplayIndex";
import styles from "./page.module.css";

export const metadata: Metadata = { title: "Replay · Argus" };

export default function ReplayPage() {
  return (
    <Suspense fallback={<div className={styles.placeholder} aria-busy="true" />}>
      <ReplayIndex />
    </Suspense>
  );
}
