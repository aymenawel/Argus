"use client";

import { useState } from "react";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { Feed } from "@/components/feed/Feed";
import type { RunSnapshot } from "@/lib/run-source";
import styles from "./SidePanel.module.css";

type Tab = "notes" | "chat";

const TABS: [Tab, string][] = [
  ["notes", "Notes"],
  ["chat", "Ask Argus"],
];

// Beside the picture: the run's notes, or a conversation about the moment on screen (D-97). One at a time, so the
// column stays calm; the choice lasts for this visit only.
export function SidePanel({ snapshot }: { snapshot: RunSnapshot }) {
  const [tab, setTab] = useState<Tab>("notes");
  const runId = snapshot.view.run.id;
  return (
    <div className={styles.side}>
      <div className={styles.tabs} role="tablist" aria-label="Beside the picture">
        {TABS.map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`side-${id}`}
            aria-selected={tab === id}
            aria-controls={`side-${id}-panel`}
            className={`${styles.tab} ${tab === id ? styles.on : ""}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className={styles.panel} role="tabpanel" id={`side-${tab}-panel`} aria-labelledby={`side-${tab}`}>
        {tab === "notes" ? (
          <Feed snapshot={snapshot} />
        ) : (
          <ChatPanel runId={runId} span={snapshot.frames.at(-1)?.t ?? 0} />
        )}
      </div>
    </div>
  );
}
