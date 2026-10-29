"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError, detectVessels, frameFromSource } from "@/lib/api";
import { inReadingOrder } from "@/lib/setup";
import type { FrameRequest, RecipeDetail, SetupVessel, VesselProposal } from "@/lib/types";
import { SetupFrame, type Region } from "./SetupFrame";
import styles from "./Step.module.css";

type Props = {
  experimentId: string;
  recipe: RecipeDetail;
  frame: FrameRequest;
  vessels: SetupVessel[];
  onChange: (vessels: SetupVessel[]) => void;
};

// SAM 3.1 proposes regions; the researcher keeps or drops them, or drags a box. Kept regions are the vessels,
// labelled A, B, C in reading order.
export function VesselsStep({ experimentId, recipe, frame, vessels, onChange }: Props) {
  const [src, setSrc] = useState<string | null>(null);
  const [frameError, setFrameError] = useState<string | null>(null);
  const [concept, setConcept] = useState(recipe.concepts[0] ?? "");
  const [proposals, setProposals] = useState<VesselProposal[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const key = JSON.stringify(frame);

  useEffect(() => {
    let live = true;
    let url: string | null = null;
    frameFromSource(experimentId, JSON.parse(key) as FrameRequest)
      .then((u) => {
        url = u;
        if (live) setSrc(u);
        else URL.revokeObjectURL(u);
      })
      .catch((e: unknown) => live && setFrameError(e instanceof ApiError ? e.detail : "No frame from the source."));
    return () => {
      live = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [experimentId, key]);

  const keep = (roi: [number, number][]) =>
    onChange(inReadingOrder([...vessels, { label: "?", role: null, condition: null, roi }]));
  const drop = (label: string) => onChange(inReadingOrder(vessels.filter((v) => v.label !== label)));

  const regions: Region[] = [
    ...vessels.map((v) => ({ key: `v:${v.label}`, roi: v.roi, label: v.label })),
    ...proposals.map((p, i) => ({ key: `p:${i}`, roi: p.roi, confidence: p.confidence })),
  ];

  return (
    <div className={styles.step}>
      <p className={styles.lead}>
        Find the vessels with SAM 3.1, then click a dashed region to keep it and a kept one to drop it. Drag on the
        frame to draw a box around a vessel it missed.
      </p>
      <div className={styles.row}>
        <label className={styles.field}>
          <span className={styles.label}>What to look for</span>
          <input
            className={`${styles.input} ${styles.short}`}
            value={concept}
            onChange={(e) => setConcept(e.target.value)}
          />
        </label>
        <Button
          variant="primary"
          disabled={busy || !concept.trim()}
          onClick={() => {
            setBusy(true);
            setError(null);
            detectVessels(experimentId, { ...frame, concept: concept.trim() })
              .then((found) => {
                setProposals(found);
                if (found.length === 0)
                  setError(`SAM 3.1 found no "${concept.trim()}". Try another word, or draw boxes.`);
              })
              .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : "The search failed."))
              .finally(() => setBusy(false));
          }}
        >
          {busy ? "Looking…" : "Find vessels"}
        </Button>
      </div>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      <SetupFrame
        src={src}
        alt="A frame from the source"
        empty={frameError ?? "Getting a frame from the source…"}
        regions={regions}
        onRegion={(k) => {
          if (k.startsWith("v:")) drop(k.slice(2));
          else {
            const i = Number(k.slice(2));
            keep(proposals[i].roi);
            setProposals(proposals.filter((_, j) => j !== i));
          }
        }}
        onDraw={keep}
      />
      {(vessels.length > 0 || proposals.length > 0) && (
        <ul className={styles.list} aria-label="Regions">
          {vessels.map((v) => (
            <li key={`v:${v.label}`} className={styles.item}>
              <span className={styles.badge}>{v.label}</span>
              <span>Vessel {v.label}</span>
              <Button variant="text" onClick={() => drop(v.label)}>
                Drop
              </Button>
            </li>
          ))}
          {proposals.map((p, i) => (
            <li key={`p:${i}`} className={styles.item}>
              <span className={styles.help}>
                Found {p.confidence != null ? `· ${Math.round(p.confidence * 100)}% sure` : ""}
              </span>
              <Button
                variant="text"
                onClick={() => {
                  keep(p.roi);
                  setProposals(proposals.filter((_, j) => j !== i));
                }}
              >
                Keep
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
