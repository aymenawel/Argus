"use client";

import { useEffect, useState } from "react";
import { getAgreement } from "@/lib/api";
import { formatRunTime } from "@/lib/scale";
import type { Agreement } from "@/lib/types";
import styles from "./AgreementTable.module.css";

type Props = { runId: string; metric: string; refresh: unknown };

const share = (x: number | null) => (x === null ? "—" : `${Math.round(x * 100)} %`);
const diff = (x: number | null) => (x === null ? "—" : x.toFixed(1));
const when = (t: number | null) => (t === null ? "never" : formatRunTime(t, 3600));

// How Argus's readings compare with a published dataset's own labels (D-71), dish by dish. Computed in code from
// stored rows; the labels are kept apart from Argus's measurements.
export function AgreementTable({ runId, metric, refresh }: Props) {
  const [result, setResult] = useState<Agreement | null>(null);

  useEffect(() => {
    let live = true;
    getAgreement(runId, metric)
      .then((a) => live && setResult(a))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [runId, metric, refresh]);

  if (!result) return null;
  const words = metric.replaceAll("_", " ");
  return (
    <section className={styles.agreement} aria-label="Agreement with the dataset's labels">
      <h3>Against {result.source}&apos;s labels</h3>
      <p className={styles.summary}>
        {result.mean_abs_diff === null
          ? `Argus hasn't measured ${words} on a labelled frame yet.`
          : `Argus vs the labels: off by ${diff(result.mean_abs_diff)} on average · the same in ` +
            `${share(result.exact_share)} of frames.`}
      </p>
      <div className={styles.scroll}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Dish</th>
              <th scope="col">Off by</th>
              <th scope="col">Same</th>
              <th scope="col">Half-way: Argus</th>
              <th scope="col">Labels</th>
              <th scope="col">Frames</th>
            </tr>
          </thead>
          <tbody>
            {result.vessels.map((v) => (
              <tr key={v.label}>
                <th scope="row">{v.label}</th>
                <td className="num">{diff(v.mean_abs_diff)}</td>
                <td className="num">{share(v.exact_share)}</td>
                <td className="num">{v.frames ? when(v.t50_argus) : "—"}</td>
                <td className="num">{when(v.t50_labels)}</td>
                <td className="num">{v.frames}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className={styles.note}>
        Half-way: when {words} first reached half its final labelled value. Frames Argus didn&apos;t measure are left
        out, not counted as zero.
      </p>
    </section>
  );
}
