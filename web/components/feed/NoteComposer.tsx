"use client";

import { useState } from "react";
import { ApiError, postNote } from "@/lib/api";
import { usePlayhead } from "@/lib/playhead";
import { formatRunTime } from "@/lib/scale";
import type { Note } from "@/lib/types";
import styles from "./NoteComposer.module.css";

type Tag = NonNullable<Note["tag"]>;

const TAGS: [Tag, string][] = [
  ["observation", "Observation"],
  ["intervention", "Intervention"],
  ["question", "Question"],
];

// What a researcher does at the bench most often, one click each: each is logged as an intervention.
const QUICK = ["Added something", "Moved a vessel", "Opened the lid"];

type Props = { runId: string; span: number; live: boolean };

// The researcher's own note at the playhead's time ("now" while following a live run). Enter saves it.
export function NoteComposer({ runId, span, live }: Props) {
  const t = usePlayhead((p) => p.t);
  const follow = usePlayhead((p) => p.follow);
  const [tag, setTag] = useState<Tag>("observation");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = (kind: Tag, words: string, clear: boolean) => {
    setBusy(true);
    setError(null);
    postNote(runId, { t, tag: kind, text: words })
      .then(() => clear && setText(""))
      .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : "The note wasn't saved."))
      .finally(() => setBusy(false));
  };

  return (
    <form
      className={styles.composer}
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim()) save(tag, text.trim(), true);
      }}
    >
      <fieldset className={styles.tags}>
        <legend className={styles.hidden}>Kind of note</legend>
        {TAGS.map(([id, label]) => (
          <label key={id} className={`${styles.tag} ${tag === id ? styles.on : ""}`}>
            <input
              type="radio"
              name={`note-tag-${runId}`}
              value={id}
              checked={tag === id}
              onChange={() => setTag(id)}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <div className={styles.row}>
        <input
          className={styles.input}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Write a note"
          aria-label="Your note"
          maxLength={4000}
          disabled={busy}
        />
        <span className={`${styles.at} num`} aria-live="polite">
          {follow && live ? "now" : `at ${formatRunTime(t, span)}`}
        </span>
      </div>
      <div className={styles.quick} aria-label="Log an intervention">
        {QUICK.map((words) => (
          <button key={words} type="button" disabled={busy} onClick={() => save("intervention", words, false)}>
            {words}
          </button>
        ))}
      </div>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
