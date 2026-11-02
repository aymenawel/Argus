"use client";

import { useEffect, useState } from "react";
import { VerdictChip } from "@/components/ui/VerdictChip";
import { AgreementTable } from "./AgreementTable";
import { Button } from "@/components/ui/Button";
import { ApiError, askVerdict, getPlans, getReviews, postReview } from "@/lib/api";
import { useReadOnly } from "@/lib/replay";
import { explanationToShow } from "@/lib/results";
import type { RunSnapshot } from "@/lib/run-source";
import type { Check, Plan, Review, Verdict, VerdictLevel } from "@/lib/types";
import styles from "./VerdictPanel.module.css";
import { VERDICT_WORDS } from "@/lib/plain";

const WORDS = VERDICT_WORDS;

const RIVAL: Record<string, string> = { ruled_out: "Ruled out", open: "Not ruled out yet", unclear: "Unclear" };

const FINDING: Record<string, string> = {
  unit_of_analysis: "What counts as a sample",
  control_comparison: "Comparing with the control",
  measurement_validity: "Measurement quality",
  confounding: "Other causes",
  multiple_comparisons: "Too many comparisons",
  early_stopping: "Stopped early",
  plan_drift: "Changed from the plan",
  over_claiming: "Saying too much",
  plain_words: "Plain words",
  numbers: "Numbers",
};

function either(levels: VerdictLevel[]): string {
  const words = levels.map((l) => WORDS[l]);
  return words.length > 1 ? `${words.slice(0, -1).join(", ")} or ${words.at(-1)}` : (words[0] ?? "");
}

function Mark({ ok }: { ok: Check["ok"] }) {
  const label = ok === true ? "Passed" : ok === false ? "Failed" : "Not settled";
  return (
    <span className={`${styles.mark} ${ok === true ? styles.ok : ok === false ? styles.failed : styles.open}`}>
      {label}
    </span>
  );
}

/** The plan this run is judged against: the first locked version, if it was locked before the run began. */
export function judgedPlan(plans: Plan[], startedAt: string): Plan | null {
  const first = plans.find((p) => p.locked_at !== null) ?? null;
  return first && first.locked_at !== null && Date.parse(first.locked_at) <= Date.parse(startedAt) ? first : null;
}

type Props = { snapshot: RunSnapshot };

// The verdict (spec §7.3): code sets which verdicts the data allows, Muse Wonder explains and a critique checks it.
// The researcher resolves rivals and confirms or dismisses it.
export function VerdictPanel({ snapshot }: Props) {
  const { run, running } = snapshot.view;
  const verdict = snapshot.verdict;
  const readOnly = useReadOnly();
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  useEffect(() => {
    getPlans(run.experiment_id)
      .then(setPlans)
      .catch(() => setPlans([]));
  }, [run.experiment_id]);

  useEffect(() => {
    getReviews(run.id)
      .then(setReviews)
      .catch(() => undefined);
  }, [run.id, verdict?.id]);

  const plan = plans === null ? null : judgedPlan(plans, run.started_at);
  const blocked =
    plans === null
      ? "Reading the plan…"
      : plan === null
        ? "Lock a plan before the run to get a verdict: a prediction written after the data can't be tested by it."
        : null;
  const now = snapshot.frames.at(-1)?.t ?? 0;

  const review = (draft: Omit<Parameters<typeof postReview>[1], "t">) =>
    postReview(run.id, { ...draft, t: now })
      .then((saved) => setReviews((r) => [...r, saved]))
      .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : "The review wasn't saved."));

  const ask = () => {
    setAsking(true);
    setError(null);
    askVerdict(run.id)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : "No verdict this time."))
      .finally(() => setAsking(false));
  };

  const decided = verdict
    ? reviews.filter((r) => r.target_kind === "verdict" && r.target_id === verdict.id).at(-1)
    : undefined;
  const resolved = new Set(
    reviews.filter((r) => r.target_kind === "rival" && r.action === "resolve").map((r) => r.target_id),
  );

  return (
    <div className={styles.panel}>
      <div className={styles.top}>
        {verdict ? (
          <VerdictChip
            level={verdict.verdict}
            provisional={verdict.provisional}
            retrospective={verdict.body.retrospective ?? false}
          />
        ) : (
          <p className={styles.none}>{readOnly ? "No verdict was asked for this run." : "No verdict yet."}</p>
        )}
        {!readOnly && (
          <Button variant={verdict ? "secondary" : "primary"} disabled={blocked !== null || asking} onClick={ask}>
            {asking ? "Judging… (about a minute)" : verdict ? "Ask again" : "Get a verdict"}
          </Button>
        )}
      </div>
      {blocked && plans !== null && !readOnly && <p className={styles.hint}>{blocked}</p>}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {verdict && (
        <Body
          verdict={verdict}
          resolved={resolved}
          onResolve={readOnly ? undefined : setResolving}
          readOnly={readOnly}
        />
      )}

      {run.source.provenance && plan?.metric && (
        <AgreementTable runId={run.id} metric={plan.metric} refresh={`${running}-${verdict?.id}`} />
      )}

      {verdict && resolving && (
        <form
          className={styles.resolve}
          onSubmit={(e) => {
            e.preventDefault();
            if (!reason.trim()) return;
            review({ target_kind: "rival", target_id: resolving, action: "resolve", comment: reason.trim() }).then(
              () => {
                setResolving(null);
                setReason("");
              },
            );
          }}
        >
          <label className={styles.resolveLabel} htmlFor="rival-reason">
            Why can “{resolving}” be ruled out?
          </label>
          <div className={styles.row}>
            <input
              id="rival-reason"
              className={styles.input}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="One line, for the record"
              maxLength={400}
              autoFocus
            />
            <Button type="submit" variant="primary" disabled={!reason.trim()}>
              Mark resolved
            </Button>
            <Button variant="text" onClick={() => setResolving(null)}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {verdict && (decided || !readOnly) && (
        <div className={styles.review}>
          {decided ? (
            <p className={styles.decided}>
              {decided.action === "confirm"
                ? readOnly
                  ? "The researcher confirmed this verdict."
                  : "You confirmed this verdict."
                : readOnly
                  ? "The researcher dismissed this verdict."
                  : "You dismissed this verdict."}
            </p>
          ) : (
            <>
              <Button
                variant="primary"
                disabled={running || verdict.provisional}
                title={running ? "Confirm once the run has ended" : undefined}
                onClick={() =>
                  review({ target_kind: "verdict", target_id: verdict.id, action: "confirm", comment: "" })
                }
              >
                Confirm
              </Button>
              <Button
                onClick={() =>
                  review({ target_kind: "verdict", target_id: verdict.id, action: "dismiss", comment: "" })
                }
              >
                Dismiss
              </Button>
              {running && <span className={styles.hint}>Confirm once the run has ended.</span>}
              {!running && verdict.provisional && (
                <span className={styles.hint}>Given while the run was going: ask again for the final verdict.</span>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

/** What the data allows now and the checks, computed in code, that decided it. */
export function VerdictChecks({ verdict }: { verdict: Verdict }) {
  return (
    <>
      <p className={styles.allowed}>
        What the data can say now: <strong>{either(verdict.allowed)}</strong>
        {verdict.fell_back && <span className={styles.fellBack}>Fell back to Muse Spark</span>}
        {verdict.body.written_by === "code" && <span className={styles.fellBack}>Explanation written by code</span>}
      </p>

      <ul className={styles.checks} aria-label="Checks computed in code">
        {verdict.checks.map((c) => (
          <li key={c.id}>
            <Mark ok={c.ok} />
            <span>{c.text}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

function Body({
  verdict,
  resolved,
  onResolve,
  readOnly,
}: {
  verdict: Verdict;
  resolved: Set<string>;
  onResolve?: (rival: string) => void; // absent in the replay: nothing can be marked
  readOnly: boolean;
}) {
  const b = verdict.body;
  const findings = b.findings ?? [];
  return (
    <div className={styles.body}>
      <VerdictChecks verdict={verdict} />

      {explanationToShow(verdict) && <p className={styles.explanation}>{b.explanation}</p>}

      {b.rivals.length > 0 && (
        <section className={styles.section}>
          <h3>Other possible causes</h3>
          <ul className={styles.rivals}>
            {b.rivals.map((r) => (
              <li key={r.name}>
                <span className={styles.rivalName}>{r.name}</span>
                <span className={styles.rivalStatus}>
                  {resolved.has(r.name)
                    ? readOnly
                      ? "Ruled out by the researcher"
                      : "Ruled out by you"
                    : (RIVAL[r.status] ?? r.status)}
                </span>
                {r.reason && <span className={styles.rivalReason}>{r.reason}</span>}
                {r.status === "open" && !resolved.has(r.name) && onResolve && (
                  <button type="button" className={styles.link} onClick={() => onResolve(r.name)}>
                    Mark resolved
                  </button>
                )}
              </li>
            ))}
          </ul>
          {!readOnly && b.rivals.some((r) => resolved.has(r.name)) && (
            <p className={styles.hint}>A cause you ruled out counts from the next verdict: ask again.</p>
          )}
        </section>
      )}

      {b.what_would_change_it && (
        <section className={styles.section}>
          <h3>What would change it</h3>
          <p>{b.what_would_change_it}</p>
        </section>
      )}

      {b.confidence && (
        <section className={styles.section}>
          <h3>Confidence: {b.confidence}</h3>
          {b.confidence_reason && <p>{b.confidence_reason}</p>}
        </section>
      )}

      {findings.length > 0 && (
        <section className={styles.section}>
          <h3>The critique</h3>
          <ul className={styles.findings}>
            {findings.map((f, i) => (
              <li key={`${f.item}-${i}`}>
                <span className={styles.findingItem}>{FINDING[f.item] ?? f.item}</span>
                <span>{f.problem}</span>
                {f.fix && <span className={styles.fix}>Fix: {f.fix}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
