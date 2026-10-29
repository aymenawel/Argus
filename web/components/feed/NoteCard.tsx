"use client";

import { playhead } from "@/lib/playhead";
import { formatRunTime } from "@/lib/scale";
import type { Note, RunEvent, VerdictLevel } from "@/lib/types";
import { EvidenceChip } from "./EvidenceChip";
import styles from "./NoteCard.module.css";

const KIND: Record<string, string> = {
  event: "Event",
  checkpoint: "Checkpoint",
  insight: "Insight",
  observation: "Observation",
  intervention: "Intervention",
  question: "Question",
};

const STATUS: Record<VerdictLevel, string> = {
  SUPPORTED: "supported",
  NOT_SUPPORTED: "not supported",
  INCONCLUSIVE: "inconclusive",
  TOO_EARLY: "too early to tell",
};

const EVENT: Record<string, string> = {
  intervention: "Intervention",
  rule: "Threshold crossed",
  camera_moved: "Camera moved",
  segment_failed: "Segmentation failed",
  quality: "Quality",
  spend: "Spend cap",
  interrupted: "Interrupted",
};

type Props = { note: Note; span: number; events: Map<string, RunEvent>; labels: Map<string, string> };

// An event's time is its event chip; the run's time and the plan's values are context, not evidence.
const CONTEXT = ["ev:", "run:", "plan:"];

function Check() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
      <path d="M2.5 6.2 5 8.6l4.5-5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

// One note: who wrote it, when, whether the claim checker passed it, its sections and the evidence behind it.
export function NoteCard({ note, span, events, labels }: Props) {
  const ai = note.author === "ai";
  const kind = note.level ?? note.tag;
  const when =
    note.t_end !== null
      ? `${formatRunTime(note.t, span)}–${formatRunTime(note.t_end, span)}`
      : formatRunTime(note.t, span);
  const b = note.body;
  const cited = (b.chips ?? [])
    .filter((chip) => !CONTEXT.some((prefix) => chip.ref.startsWith(prefix)))
    .map((chip) => (
      <EvidenceChip key={chip.ref} text={chip.display} title={chip.label} t={chip.t} vesselId={chip.vessel_id} />
    ));
  const happened = note.evidence
    .map((id) => events.get(id))
    .filter((e): e is RunEvent => e !== undefined)
    .map((e) => (
      <EvidenceChip
        key={e.id}
        text={`${EVENT[e.kind] ?? e.kind}${e.vessel_id && labels.has(e.vessel_id) ? ` · ${labels.get(e.vessel_id)}` : ""} at ${formatRunTime(e.t_start, span)}`}
        title={String(e.detail.message ?? EVENT[e.kind] ?? e.kind)}
        t={e.t_start}
        vesselId={e.vessel_id}
      />
    ));

  return (
    <article className={`${styles.card} ${ai ? "" : styles.mine}`}>
      <header className={styles.head}>
        <span className={styles.author}>{ai ? "Argus" : "You"}</span>
        {kind && <span className={styles.kind}>{KIND[kind] ?? kind}</span>}
        <button
          type="button"
          className={`${styles.time} num`}
          title="Show this moment"
          onClick={() => playhead.setT(note.t)}
        >
          {when}
        </button>
        {note.check_status === "passed" && (
          <span className={styles.checked} title="Every number in this note was checked against the measurements">
            <Check />
            Checked
          </span>
        )}
        {note.check_status === "fallback" && <span className={styles.code}>Written by code</span>}
      </header>

      {ai ? (
        <div className={styles.sections}>
          {b.observation && <p className={styles.observation}>{b.observation}</p>}
          {b.interpretation && <p>{b.interpretation}</p>}
          {b.hypothesis_status && (
            <p className={styles.line}>
              <span className={styles.label}>Hypothesis</span> {STATUS[b.hypothesis_status]}
            </p>
          )}
          {b.confidence && (
            <p className={styles.line}>
              <span className={styles.label}>Confidence</span> {b.confidence}
              {b.confidence_reason ? ` · ${b.confidence_reason}` : ""}
            </p>
          )}
          {b.rival_explanations && b.rival_explanations.length > 0 && (
            <p className={styles.line}>
              <span className={styles.label}>Rivals</span> {b.rival_explanations.join("; ")}
            </p>
          )}
          {b.next_step && (
            <p className={styles.line}>
              <span className={styles.label}>Suggestion</span> {b.next_step}
            </p>
          )}
          {b.question_for_researcher && <p className={styles.question}>{b.question_for_researcher}</p>}
          {note.check_status === "fallback" && b.reason && <p className={styles.reason}>Why: {b.reason}.</p>}
        </div>
      ) : (
        <p className={styles.text}>{b.text}</p>
      )}

      {(cited.length > 0 || happened.length > 0) && (
        <div className={styles.chips} aria-label="Evidence">
          {happened}
          {cited}
        </div>
      )}
    </article>
  );
}
