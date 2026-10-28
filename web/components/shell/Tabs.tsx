import Link from "next/link";
import styles from "./Tabs.module.css";

type Tab = { href: string; label: string };

// Page sections as a pill track. These are links between places, so they are a nav, not an ARIA tablist.
export function Tabs({ items, active, label = "Sections" }: { items: Tab[]; active: string; label?: string }) {
  return (
    <nav className={styles.track} aria-label={label}>
      {items.map((item) => {
        const on = item.href === active;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`${styles.tab} ${on ? styles.on : ""}`}
            aria-current={on ? "page" : undefined}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
