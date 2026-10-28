import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Suspense } from "react";
import { Rail, RailFallback } from "@/components/shell/Rail";
import { THEME_SCRIPT } from "@/lib/theme";
import styles from "./layout.module.css";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Argus",
  description: "An AI lab partner that watches experiments and measures them in real units.",
};

// suppressHydrationWarning: THEME_SCRIPT may set data-theme on <html> before React hydrates.
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <a className={styles.skip} href="#content">
          Skip to content
        </a>
        <div className={styles.app}>
          <Suspense fallback={<RailFallback />}>
            <Rail />
          </Suspense>
          <main id="content" className={styles.content}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
