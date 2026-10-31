"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError, getMedia, makeMedia, mediaUrl } from "@/lib/api";
import { videoRow } from "@/lib/media";
import { useReadOnly } from "@/lib/replay";
import type { MediaKind, MediaView } from "@/lib/types";
import styles from "./VideosCard.module.css";

const VIDEOS: { kind: MediaKind; name: string; about: string }[] = [
  { kind: "timelapse", name: "Timelapse", about: "The whole run in 20 s with its curves" },
  { kind: "reel", name: "Highlights reel", about: "The moments that mattered, 30–60 s" },
];

const POLL_MS = 2000;

// The run's videos (D-84, D-85): made by the worker from stored records only, in the background. In the public
// replay nothing can be made; a video the bundle carries can still be downloaded.
export function VideosCard({ runId }: { runId: string }) {
  const readOnly = useReadOnly();
  const [view, setView] = useState<{ runId: string; media: MediaView } | null>(null);
  const [error, setError] = useState<{ kind: MediaKind | null; text: string } | null>(null);
  const media = view?.runId === runId ? view.media : null;

  const load = useCallback(
    () =>
      getMedia(runId)
        .then((found) => setView({ runId, media: found }))
        .catch((e: unknown) => setError({ kind: null, text: e instanceof ApiError ? e.detail : String(e) })),
    [runId],
  );

  useEffect(() => {
    load();
  }, [load]);

  const making = media !== null && Object.values(media).some((s) => s.state === "running");
  useEffect(() => {
    if (!making) return;
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [making, load]);

  const make = (kind: MediaKind) => {
    setError(null);
    makeMedia(runId, kind)
      .then((state) => setView((v) => (v && v.runId === runId ? { runId, media: { ...v.media, [kind]: state } } : v)))
      .catch((e: unknown) => setError({ kind, text: e instanceof ApiError ? e.detail : String(e) }));
  };

  if (media === null) {
    return error ? (
      <p className={styles.error} role="alert">
        Videos aren&apos;t available: {error.text}
      </p>
    ) : (
      <p className={styles.none}>Reading the videos…</p>
    );
  }

  return (
    <ul className={styles.list}>
      {VIDEOS.map(({ kind, name, about }) => {
        const row = videoRow(media[kind], readOnly);
        return (
          <li key={kind} className={styles.row}>
            <div className={styles.text}>
              <span className={styles.name}>{name}</span>
              <span className={styles.about}>{about}</span>
            </div>
            <span className={`${styles.status} num`} role="status">
              {row.status}
            </span>
            <div className={styles.actions}>
              {row.download && (
                <a className={styles.download} href={mediaUrl(runId, kind)} download>
                  Download
                </a>
              )}
              {row.action && (
                <Button variant={row.action === "make" ? "primary" : "secondary"} onClick={() => make(kind)}>
                  {row.action === "make" ? "Make" : "Make again"}
                </Button>
              )}
            </div>
            {error?.kind === kind && (
              <p className={styles.error} role="alert">
                {error.text}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
