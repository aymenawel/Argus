"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Mark } from "@/components/brand/Mark";
import { isReplay } from "@/lib/replay";
import styles from "./Rail.module.css";

type NavItem = { href: string; label: string; icon: ReactNode };

const svg = (children: ReactNode) => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    aria-hidden="true"
  >
    {children}
  </svg>
);

// The design-system kit (/kit) is for building Argus, so it is reachable by its address but not listed here.
const MAIN: NavItem[] = [
  {
    href: "/",
    label: "Experiments",
    icon: svg(
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M3 9h18M9 9v11" />
      </>,
    ),
  },
];

const SETTINGS: NavItem = {
  href: "/settings",
  label: "Settings",
  icon: svg(
    <>
      <path d="M4 7h10M18 7h2M4 17h4M12 17h8" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="10" cy="17" r="2" />
    </>,
  ),
};

// The public replay (D-83) offers only its runs and the source code.
const REPLAY: NavItem = { href: "/replay", label: "Replays", icon: MAIN[0].icon };
const SOURCE = "https://github.com/aymenawel/Argus";
const SOURCE_ICON = svg(
  <>
    <path d="M9 7l-5 5 5 5M15 7l5 5-5 5" />
  </>,
);

function isActive(href: string, pathname: string) {
  if (href === "/") return pathname === "/" || pathname.startsWith("/experiments");
  return pathname === href || pathname.startsWith(`${href}/`);
}

function RailLink({ item, pathname }: { item: NavItem; pathname: string | null }) {
  const active = pathname !== null && isActive(item.href, pathname);
  return (
    <Link
      href={item.href}
      className={`${styles.item} ${active ? styles.active : ""}`}
      aria-label={item.label}
      aria-current={active ? "page" : undefined}
      title={item.label}
    >
      {item.icon}
    </Link>
  );
}

function RailNav({ pathname }: { pathname: string | null }) {
  return (
    <nav className={styles.rail} aria-label="Argus">
      <span className={styles.mark}>
        <Mark />
      </span>
      {(isReplay() ? [REPLAY] : MAIN).map((item) => (
        <RailLink key={item.href} item={item} pathname={pathname} />
      ))}
      <div className={styles.bottom}>
        {isReplay() ? (
          <a
            href={SOURCE}
            className={styles.item}
            aria-label="Source on GitHub"
            title="Source on GitHub"
            target="_blank"
            rel="noreferrer"
          >
            {SOURCE_ICON}
          </a>
        ) : (
          <RailLink item={SETTINGS} pathname={pathname} />
        )}
      </div>
    </nav>
  );
}

export function Rail() {
  return <RailNav pathname={usePathname()} />;
}

/** The rail before the URL is known (prerendering a page whose path has a dynamic part): nothing is active. */
export function RailFallback() {
  return <RailNav pathname={null} />;
}
