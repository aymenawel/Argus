import type { ReactNode } from "react";
import styles from "./PageHeader.module.css";

type PageHeaderProps = {
  crumb?: ReactNode;
  title: string;
  finding?: ReactNode;
  actions?: ReactNode;
};

// The page's one h1, with the finding line: what the data on this page says, in a sentence.
export function PageHeader({ crumb, title, finding, actions }: PageHeaderProps) {
  return (
    <header className={styles.header}>
      {crumb && <div className={styles.crumb}>{crumb}</div>}
      <div className={styles.row}>
        <div className={styles.text}>
          <h1 className={styles.title}>{title}</h1>
          {finding && <p className={styles.finding}>{finding}</p>}
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
    </header>
  );
}
