import type { Experiment, ExperimentStatus, RecipeSummary } from "@/lib/types";
import styles from "./ExperimentsTable.module.css";

const STATUS: Record<ExperimentStatus, { label: string; className: string }> = {
  draft: { label: "Setting up", className: styles.draft },
  locked: { label: "Plan locked", className: styles.locked },
  running: { label: "Running", className: styles.running },
  finished: { label: "Finished", className: styles.finished },
};

const created = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function Head() {
  return (
    <thead>
      <tr>
        <th scope="col">Experiment</th>
        <th scope="col">State</th>
        <th scope="col" className={styles.right}>
          Created
        </th>
      </tr>
    </thead>
  );
}

export function ExperimentsTable({ experiments, recipes }: { experiments: Experiment[]; recipes: RecipeSummary[] }) {
  const recipeTitle = new Map(recipes.map((r) => [r.id, r.title]));
  return (
    <div className={styles.scroll}>
      <table className={styles.table}>
        <caption className={styles.hidden}>Experiments, newest first</caption>
        <Head />
        <tbody>
          {experiments.map((e) => (
            <tr key={e.id}>
              <td>
                <span className={styles.title}>{e.title}</span>
                <span className={styles.sub}>{recipeTitle.get(e.recipe_id) ?? e.recipe_id}</span>
              </td>
              <td>
                <span className={`${styles.state} ${STATUS[e.status].className}`}>
                  <span className={styles.dot} aria-hidden="true" />
                  {STATUS[e.status].label}
                </span>
              </td>
              <td className={`${styles.right} num`}>
                <time dateTime={e.created_at}>{created.format(new Date(e.created_at))}</time>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Placeholder rows built from the same cells as real rows, so nothing jumps when the data lands.
export function ExperimentsTableSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className={styles.scroll} aria-busy="true">
      <table className={styles.table}>
        <caption className={styles.hidden}>Loading experiments</caption>
        <Head />
        <tbody>
          {Array.from({ length: rows }, (_, i) => (
            <tr key={i} aria-hidden="true">
              <td>
                <span className={styles.title}>
                  <span className={styles.bar} style={{ width: `${46 - i * 8}%` }} />
                </span>
                <span className={styles.sub}>
                  <span className={styles.bar} style={{ width: "22%" }} />
                </span>
              </td>
              <td>
                <span className={styles.bar} style={{ width: 84 }} />
              </td>
              <td className={styles.right}>
                <span className={styles.bar} style={{ width: 88 }} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
