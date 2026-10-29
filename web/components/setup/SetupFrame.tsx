"use client";

import { useRef, useState, type PointerEvent } from "react";
import styles from "./SetupFrame.module.css";

export type Region = {
  key: string;
  roi: [number, number][];
  label?: string; // a kept vessel
  confidence?: number | null; // a SAM proposal not kept yet
};

type Props = {
  src: string | null;
  alt: string;
  regions?: Region[];
  outlines?: [number, number][][];
  ruler?: [number, number][]; // the points clicked so far (0, 1 or 2)
  onRegion?: (key: string) => void;
  onDraw?: (roi: [number, number][]) => void; // a box dragged on the frame
  onPoint?: (point: [number, number]) => void; // a click, for the ruler
  empty?: string;
};

const MIN_BOX_PX = 12;
const points = (polygon: [number, number][]) => polygon.map(([x, y]) => `${x},${y}`).join(" ");

function topCentre(roi: [number, number][]): [number, number] {
  const xs = roi.map(([x]) => x);
  return [(Math.min(...xs) + Math.max(...xs)) / 2, Math.min(...roi.map(([, y]) => y))];
}

// A frame to set up on, in its own pixels: vessels (solid, labelled), SAM's proposals (dashed, with confidence),
// outlines from a check, and a box being drawn or a ruler being clicked.
export function SetupFrame({ src, alt, regions = [], outlines = [], ruler, onRegion, onDraw, onPoint, empty }: Props) {
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  const [drag, setDrag] = useState<{ from: [number, number]; to: [number, number] } | null>(null);
  const svg = useRef<SVGSVGElement>(null);

  const at = (e: PointerEvent): [number, number] => {
    const box = svg.current!.getBoundingClientRect();
    return [((e.clientX - box.left) / box.width) * size!.w, ((e.clientY - box.top) / box.height) * size!.h];
  };

  const drawing = onDraw !== undefined || onPoint !== undefined;
  return (
    <div className={styles.frame} style={{ aspectRatio: size ? `${size.w} / ${size.h}` : "16 / 9" }}>
      {src ? (
        // A frame from the local worker; next/image would only add a resizing hop.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          className={styles.image}
          src={src}
          alt={alt}
          onLoad={(e) => setSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
        />
      ) : (
        <p className={styles.empty}>{empty ?? "No frame yet"}</p>
      )}
      {size && (
        <svg
          ref={svg}
          className={`${styles.overlay} ${drawing ? styles.drawing : ""}`}
          viewBox={`0 0 ${size.w} ${size.h}`}
          onPointerDown={(e) => {
            if (e.target !== e.currentTarget) return; // a region handles its own click
            if (onPoint) {
              onPoint(at(e));
              return;
            }
            if (!onDraw) return;
            e.currentTarget.setPointerCapture(e.pointerId);
            const p = at(e);
            setDrag({ from: p, to: p });
          }}
          onPointerMove={(e) => drag && setDrag({ ...drag, to: at(e) })}
          onPointerUp={() => {
            if (!drag || !onDraw) return;
            const [x0, x1] = [drag.from[0], drag.to[0]].sort((a, b) => a - b);
            const [y0, y1] = [drag.from[1], drag.to[1]].sort((a, b) => a - b);
            setDrag(null);
            if (x1 - x0 >= MIN_BOX_PX && y1 - y0 >= MIN_BOX_PX) {
              onDraw([
                [Math.round(x0), Math.round(y0)],
                [Math.round(x1), Math.round(y0)],
                [Math.round(x1), Math.round(y1)],
                [Math.round(x0), Math.round(y1)],
              ]);
            }
          }}
        >
          {outlines.map((polygon, i) => (
            <polygon key={`o${i}`} points={points(polygon)} className={styles.outline} />
          ))}
          {regions.map((r) => (
            <polygon
              key={r.key}
              points={points(r.roi)}
              className={r.label ? styles.vessel : styles.proposal}
              onPointerDown={(e) => {
                e.stopPropagation();
                onRegion?.(r.key);
              }}
            />
          ))}
          {drag && (
            <rect
              className={styles.box}
              x={Math.min(drag.from[0], drag.to[0])}
              y={Math.min(drag.from[1], drag.to[1])}
              width={Math.abs(drag.to[0] - drag.from[0])}
              height={Math.abs(drag.to[1] - drag.from[1])}
            />
          )}
          {ruler && ruler.length === 2 && (
            <line className={styles.ruler} x1={ruler[0][0]} y1={ruler[0][1]} x2={ruler[1][0]} y2={ruler[1][1]} />
          )}
          {ruler?.map(([x, y], i) => (
            <circle key={`r${i}`} className={styles.point} cx={x} cy={y} r={Math.max(size.w, size.h) / 160} />
          ))}
        </svg>
      )}
      {size &&
        regions.map((r) => {
          const [x, y] = topCentre(r.roi);
          const text = r.label ?? (r.confidence != null ? `${Math.round(r.confidence * 100)}%` : "?");
          return (
            <span
              key={`t${r.key}`}
              className={`${styles.tag} ${r.label ? "" : styles.proposalTag} num`}
              style={{ left: `${(x / size.w) * 100}%`, top: `max(6px, calc(${(y / size.h) * 100}% - 30px))` }}
              aria-hidden="true"
            >
              {text}
            </span>
          );
        })}
    </div>
  );
}
