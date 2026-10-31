import type { BundleManifest } from "@/lib/replay";
import styles from "./ReplayBanner.module.css";

const day = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

// Every page of the public replay says what it is (D-83): a recording, not a live run, and published data with its
// credit and licence (D-70).
export function ReplayBanner({ manifest }: { manifest: BundleManifest | null }) {
  return (
    <div className={styles.banner} role="note">
      <p className={styles.lead}>
        {manifest
          ? `Replay · recorded ${day(manifest.recorded)} · nothing on this page is live`
          : "Replay · nothing on this page is live"}
      </p>
      {manifest?.source_label === "published data" && manifest.credit && (
        <p>
          Published data:{" "}
          {manifest.dataset_url ? (
            <a href={manifest.dataset_url} target="_blank" rel="noreferrer">
              {manifest.credit}
            </a>
          ) : (
            manifest.credit
          )}
          {manifest.licence ? ` · ${manifest.licence}` : ""}
        </p>
      )}
      <p>Everything shown was built Oct 27 – Nov 4, 2026</p>
    </div>
  );
}
