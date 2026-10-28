import type { Metadata } from "next";
import { Mark, type MarkState } from "@/components/brand/Mark";
import { PageHeader } from "@/components/shell/PageHeader";
import { Tabs } from "@/components/shell/Tabs";
import { ThemeSwitch } from "@/components/shell/ThemeSwitch";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { VerdictChip } from "@/components/ui/VerdictChip";
import type { RunMode, VerdictLevel } from "@/lib/types";
import styles from "./page.module.css";

export const metadata: Metadata = { title: "Kit · Argus" };

const SWATCHES: { token: string; role: string }[] = [
  { token: "--ground", role: "Ground" },
  { token: "--surface", role: "Surface" },
  { token: "--raised", role: "Tile" },
  { token: "--sunk", role: "Track" },
  { token: "--text", role: "Ink" },
  { token: "--muted", role: "Muted text" },
  { token: "--accent", role: "Teal" },
  { token: "--accent-tint", role: "Teal tint" },
  { token: "--pos", role: "Positive" },
  { token: "--neg", role: "Negative" },
  { token: "--warn", role: "Notice" },
  { token: "--frame", role: "Camera frame" },
];

const SHAPES: { label: string; radius: string; tone: string; w: number; h: number }[] = [
  { label: "Panel 20", radius: "var(--r-card)", tone: "var(--raised)", w: 96, h: 72 },
  { label: "Video 16", radius: "var(--r-media)", tone: "var(--frame)", w: 84, h: 60 },
  { label: "Tile 14", radius: "var(--r-tile)", tone: "var(--raised)", w: 72, h: 52 },
  { label: "Lane 10", radius: "var(--r-small)", tone: "var(--raised)", w: 64, h: 40 },
  { label: "Control, pill", radius: "var(--r-pill)", tone: "var(--primary-bg)", w: 84, h: 34 },
];

const SOURCES: RunMode[] = ["live", "replay", "imported"];
const VERDICTS: VerdictLevel[] = ["SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE", "TOO_EARLY"];
const MARKS: { state: MarkState; label: string }[] = [
  { state: "resting", label: "Resting" },
  { state: "watching", label: "Watching" },
  { state: "locked", label: "Locked" },
];

const TYPE: { name: string; size: string; weight: number; sample: string }[] = [
  { name: "Title 26", size: "var(--fs-title)", weight: 600, sample: "Salt-stress germination" },
  { name: "Lead 18", size: "var(--fs-lead)", weight: 600, sample: "Jars C and F trail" },
  { name: "Section 16", size: "var(--fs-section)", weight: 600, sample: "Readouts" },
  { name: "Body 14", size: "var(--fs-body)", weight: 400, sample: "3 of 16 beans sprouted at 41 h." },
  { name: "Small 13", size: "var(--fs-sm)", weight: 400, sample: "41:20 / 72:00 · $0.84 of $10" },
  { name: "Label 12", size: "var(--fs-xs)", weight: 500, sample: "0123456789" },
];

const mic = (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    aria-hidden="true"
  >
    <rect x="9" y="3" width="6" height="11" rx="3" />
    <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
  </svg>
);

const more = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <circle cx="5" cy="12" r="1.8" />
    <circle cx="12" cy="12" r="1.8" />
    <circle cx="19" cy="12" r="1.8" />
  </svg>
);

export default function KitPage() {
  return (
    <>
      <PageHeader
        crumb={
          <>
            <span>Argus Labs</span>
            <span className={styles.faint}>/</span>
            <span>Design system</span>
          </>
        }
        title="Kit"
        finding="Every shared piece in every state. Switch the theme to check light and dark; the System setting follows your computer."
        actions={<ThemeSwitch />}
      />

      <div className={styles.grid}>
        <Panel title="Colour" meta="Tokens of the current theme" className={styles.wide}>
          <div className={styles.swatches}>
            {SWATCHES.map((s) => (
              <div key={s.token}>
                <div className={styles.swatch} style={{ background: `var(${s.token})` }} />
                <div className={styles.swatchRole}>{s.role}</div>
                <div className={styles.faint}>{s.token}</div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Source" meta="Only LIVE moves">
          <div className={styles.row}>
            {SOURCES.map((source) => (
              <Badge key={source} source={source} />
            ))}
          </div>
        </Panel>

        <Panel title="Verdicts" meta="Dashed while provisional">
          <div className={styles.stack}>
            <div className={styles.row}>
              {VERDICTS.map((level) => (
                <VerdictChip key={level} level={level} />
              ))}
            </div>
            <div className={styles.row}>
              {VERDICTS.map((level) => (
                <VerdictChip key={level} level={level} provisional />
              ))}
            </div>
          </div>
        </Panel>

        <Panel title="Buttons" meta="Pills; press scales to .97">
          <div className={styles.stack}>
            <div className={styles.row}>
              <Button variant="primary">Lock plan</Button>
              <Button icon={mic}>Voice note</Button>
              <Button variant="text">Skip</Button>
              <Button icon={more} aria-label="More actions" title="More actions" />
            </div>
            <div className={styles.row}>
              <Button variant="primary" disabled>
                Lock plan
              </Button>
              <Button disabled>Voice note</Button>
              <Button variant="text" disabled>
                Skip
              </Button>
            </div>
          </div>
        </Panel>

        <Panel title="Tabs" meta="The active tab is an ink pill">
          <Tabs
            label="Example sections"
            active="#run"
            items={[
              { href: "#run", label: "Run" },
              { href: "#results", label: "Results" },
              { href: "#next", label: "Next run" },
            ]}
          />
        </Panel>

        <Panel title="Shape" meta="Nested corners step down">
          <div className={styles.shapes}>
            {SHAPES.map((s) => (
              <div key={s.label} className={styles.shape}>
                <div style={{ width: s.w, height: s.h, borderRadius: s.radius, background: s.tone }} />
                <div className={styles.caption}>{s.label}</div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="The mark at work" meta="Also the loader">
          <div className={styles.marks}>
            {MARKS.map((m) => (
              <div key={m.state} className={styles.markCell}>
                <Mark state={m.state} size={72} />
                <div className={styles.caption}>{m.label}</div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Type" meta="One face; digits line up" className={styles.wide}>
          <div className={styles.typeGrid}>
            <div className={styles.stack}>
              {TYPE.map((t) => (
                <div key={t.name} className={styles.typeRow}>
                  <span className={styles.caption}>{t.name}</span>
                  <span style={{ fontSize: t.size, fontWeight: t.weight }}>{t.sample}</span>
                </div>
              ))}
            </div>
            <div className={styles.tiles}>
              <div className={styles.tile}>
                <div className={styles.tileKey}>Jar B</div>
                <div className={`${styles.readout} num`}>
                  36.7<span className={styles.pm}> ± 1.9 mm</span>
                </div>
              </div>
              <div className={styles.tile}>
                <div className={styles.tileKey}>Jar F</div>
                <div className={`${styles.readout} num`}>
                  3.8<span className={styles.pm}> ± 0.4 mm</span>
                </div>
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}
