import type { Metadata } from "next";
import { ModelChoice } from "@/components/settings/ModelChoice";
import { PageHeader } from "@/components/shell/PageHeader";
import { ThemeSwitch } from "@/components/shell/ThemeSwitch";
import { Panel } from "@/components/ui/Panel";
import styles from "./page.module.css";

export const metadata: Metadata = { title: "Settings · Argus" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader crumb="Argus Labs" title="Settings" />
      <div className={styles.panels}>
        <Panel title="Everyday model" meta="Drafting, notes and plan drafts">
          <ModelChoice />
        </Panel>
        <Panel title="Appearance">
          <ThemeSwitch />
        </Panel>
      </div>
    </>
  );
}
