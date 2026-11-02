import { formatDuration, formatPair } from "@/lib/chart";
import { coverageLines } from "@/lib/misses";
import type { FitsView } from "@/lib/types";
import styles from "./FitTable.module.css";
import { curveWords, roleWord, sentence } from "@/lib/plain";

// Each vessel's fitted half-way time, rate and plateau with ±, or why it has none, and how often its object was found,
// and how: by name, by pointing SAM at the change, or by code (D-90, D-93). Numbers come from the worker's fits; this
// only rounds them (the ± first).
export function FitTable({ fits }: { fits: FitsView }) {
  const unit = fits.unit;
  const span = Math.max(0, ...fits.vessels.flatMap((v) => v.readings.map(([t]) => t)));
  return (
    <div className={styles.scroll}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Sample</th>
            <th scope="col">Condition</th>
            <th scope="col">Found</th>
            <th scope="col">Time to get half-way</th>
            <th scope="col">Speed</th>
            <th scope="col">Levels off at</th>
            <th scope="col">Curve</th>
          </tr>
        </thead>
        <tbody>
          {fits.vessels.map((v) => {
            const fit = v.fit;
            const status = !fit
              ? "No readings"
              : !fit.ok
                ? `No curve fits: ${fit.reason}`
                : !fit.reached
                  ? "Still rising at the end"
                  : `${sentence(curveWords(fit.curve))} curve`;
            const [found, how, missed] = coverageLines(v.coverage, span);
            return (
              <tr key={v.vessel_id}>
                <th scope="row">
                  {v.label}
                  <span className={styles.role}>{roleWord(v.role)}</span>
                </th>
                <td>{v.condition ? String(v.condition.value) : "—"}</td>
                <td className="num">
                  {found}
                  {how && <span className={styles.sub}>{how}</span>}
                  {missed && <span className={styles.sub}>{missed}</span>}
                </td>
                <td className="num">{fit?.ok && fit.half_time_h ? formatDuration(fit.half_time_h) : "—"}</td>
                <td className="num">{fit?.ok && fit.rate_per_h ? formatPair(fit.rate_per_h, `${unit}/h`) : "—"}</td>
                <td className="num">{fit?.ok && fit.plateau ? formatPair(fit.plateau, unit) : "—"}</td>
                <td className={fit?.ok ? styles.ok : styles.refused}>{status}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
