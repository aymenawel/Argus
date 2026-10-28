import type { ReactNode } from "react";
import styles from "./Panel.module.css";

type PanelProps = {
  title?: string;
  meta?: ReactNode;
  className?: string;
  children: ReactNode;
};

// A white surface on the ground. No border: the tone step does the separating.
export function Panel({ title, meta, className, children }: PanelProps) {
  return (
    <section className={`${styles.panel} ${className ?? ""}`}>
      {(title || meta) && (
        <div className={styles.head}>
          {title && <h2>{title}</h2>}
          {meta && <span className={styles.meta}>{meta}</span>}
        </div>
      )}
      <div className={styles.body}>{children}</div>
    </section>
  );
}
