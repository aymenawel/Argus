"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Mark } from "@/components/brand/Mark";
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
  {
    href: "/views",
    label: "Views",
    icon: svg(
      <>
        <rect x="4" y="4" width="7" height="7" rx="2" />
        <rect x="13" y="4" width="7" height="7" rx="2" />
        <rect x="4" y="13" width="7" height="7" rx="2" />
        <path d="M14 19l2.5-4 2.5 4z" />
      </>,
    ),
  },
  {
    href: "/kit",
    label: "Kit",
    icon: svg(
      <>
        <circle cx="8" cy="8" r="4" />
        <rect x="13" y="13" width="7" height="7" rx="2" />
        <path d="M13 4h7M16.5 4v6M4 16h6M4 20h6" />
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
      {MAIN.map((item) => (
        <RailLink key={item.href} item={item} pathname={pathname} />
      ))}
      <div className={styles.bottom}>
        <RailLink item={SETTINGS} pathname={pathname} />
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
