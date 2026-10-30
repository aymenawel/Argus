import { formatPair } from "@/lib/chart";
import type { FitsView } from "@/lib/types";
import styles from "./FitTable.module.css";

// Each vessel's fitted half-way time, rate and plateau with ±, or why it has none. Numbers come from the worker's
// fits; this only rounds them (the ± first).
export function FitTable({ fits }: { fits: FitsView }) {
  const unit = fits.unit;
  return (
    <div className={styles.scroll}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Vessel</th>
            <th scope="col">Condition</th>
            <th scope="col">Half-way time</th>
            <th scope="col">Rate</th>
            <th scope="col">Plateau</th>
            <th scope="col">Fit</th>
          </tr>
        </thead>
        <tbody>
          {fits.vessels.map((v) => {
            const fit = v.fit;
            const status = !fit
              ? "No readings"
              : !fit.ok
                ? `No fit: ${fit.reason}`
                : !fit.reached
                  ? "Still rising at the end"
                  : `${fit.curve} curve`;
            return (
              <tr key={v.vessel_id}>
                <th scope="row">
                  {v.label}
                  <span className={styles.role}>{v.role}</span>
                </th>
                <td>{v.condition ? String(v.condition.value) : "—"}</td>
                <td className="num">{fit?.ok && fit.half_time_h ? formatPair(fit.half_time_h, "h") : "—"}</td>
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
