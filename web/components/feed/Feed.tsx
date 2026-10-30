"use client";

import { useMemo } from "react";
import { playhead, usePlayhead } from "@/lib/playhead";
import type { RunSnapshot } from "@/lib/run-source";
import { NoteCard } from "./NoteCard";
import { NoteComposer } from "./NoteComposer";
import styles from "./Feed.module.css";

// The run's notes, newest first, up to the playhead's moment like everything else on the Run view (spec §9.3).
export function Feed({ snapshot }: { snapshot: RunSnapshot }) {
  const t = usePlayhead((p) => p.t);
  const follow = usePlayhead((p) => p.follow);
  const span = snapshot.frames.at(-1)?.t ?? 0;
  const events = useMemo(() => new Map(snapshot.events.map((e) => [e.id, e])), [snapshot.events]);
  const labels = useMemo(() => new Map(snapshot.view.vessels.map((v) => [v.id, v.label])), [snapshot.view.vessels]);
  const shown = useMemo(
    () => (follow ? snapshot.notes : snapshot.notes.filter((n) => n.t <= t + 1e-6)).toReversed(),
    [snapshot.notes, follow, t],
  );
  const later = snapshot.notes.length - shown.length;

  return (
    <div className={styles.feed}>
      <NoteComposer runId={snapshot.view.run.id} span={span} live={snapshot.view.running} />
      {later > 0 && (
        <button type="button" className={styles.later} onClick={() => playhead.followLive()}>
          {later} later {later === 1 ? "note" : "notes"} · show all
        </button>
      )}
      {shown.length > 0 ? (
        <ol className={styles.list} aria-label="Notes, newest first">
          {shown.map((note) => (
            <li key={note.id}>
              <NoteCard
                note={note}
                span={span}
                events={events}
                labels={labels}
                model={note.model_call_id ? snapshot.models[note.model_call_id] : undefined}
              />
            </li>
          ))}
        </ol>
      ) : (
        <p className={styles.empty}>
          {later > 0
            ? "No notes before this moment."
            : "No notes yet. Argus notes what happens and sums up the run at checkpoints; add your own above."}
        </p>
      )}
      {snapshot.rejected > 0 && (
        <p
          className={styles.rejected}
          title="Answers that cited a number the measurements don't hold, or claimed more than the data allows"
        >
          Rejected by the claim checker: <span className="num">{snapshot.rejected}</span>
        </p>
      )}
    </div>
  );
}
