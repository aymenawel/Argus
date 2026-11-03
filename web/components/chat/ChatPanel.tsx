"use client";

import { useEffect, useRef, useState } from "react";
import { EvidenceChip } from "@/components/feed/EvidenceChip";
import { ApiError, askChat, errorText, getChat } from "@/lib/api";
import { cleanQuestion, MAX_QUESTION, momentLabel, showSuggestions, SUGGESTIONS } from "@/lib/chat";
import { subscribe } from "@/lib/events";
import { chipTitle } from "@/lib/plain";
import { usePlayhead } from "@/lib/playhead";
import { useReadOnly } from "@/lib/replay";
import type { ChatMessage } from "@/lib/types";
import styles from "./ChatPanel.module.css";

type Props = { runId: string; span: number };

const added = (list: ChatMessage[] | null, message: ChatMessage) =>
  list === null ? [message] : list.some((m) => m.id === message.id) ? list : [...list, message];

// Ask Argus (D-97): questions about the moment on the playhead ("now" while following a live run), answered from
// what Argus measured. In the public demo the saved conversation is shown and nothing can be asked.
export function ChatPanel({ runId, span }: Props) {
  const readOnly = useReadOnly();
  const t = usePlayhead((p) => p.t);
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let live = true;
    getChat(runId)
      .then((list) => live && setMessages(list))
      .catch((e: unknown) => live && setLoadError(e instanceof ApiError ? errorText(e) : "The questions didn't load."));
    const unsubscribe = readOnly
      ? () => {}
      : subscribe((type, data) => {
          const event = data as { run_id?: string; message?: ChatMessage };
          if (type === "chat" && event.run_id === runId && event.message) {
            const message = event.message;
            setMessages((list) => added(list, message));
          }
        });
    return () => {
      live = false;
      unsubscribe();
    };
  }, [runId, readOnly]);

  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest" });
  }, [messages?.length, busy]);

  const ask = (words: string) => {
    const question = cleanQuestion(words);
    if (question === null || busy) return;
    setBusy(true);
    setError(null);
    askChat(runId, t, question)
      .then((message) => {
        setMessages((list) => added(list, message));
        setText("");
      })
      .catch((e: unknown) => setError(e instanceof ApiError ? e.detail : "Argus couldn't answer just now. Try again."))
      .finally(() => setBusy(false));
  };

  return (
    <div className={styles.chat}>
      {readOnly && <p className={styles.saved}>Saved questions from the app</p>}
      <div className={styles.scroll}>
        {messages === null ? (
          <p className={styles.empty} role={loadError ? "alert" : undefined} aria-busy={loadError ? undefined : true}>
            {loadError ?? "Loading…"}
          </p>
        ) : messages.length === 0 && !busy ? (
          <p className={styles.empty}>
            {readOnly
              ? "No questions were asked on this run."
              : "Ask about what you're watching. Argus answers about the moment on screen, using only what it measured."}
          </p>
        ) : (
          <ol className={styles.list} aria-label="Questions and answers">
            {messages.map((m) => (
              <li key={m.id} className={styles.exchange}>
                <p className={styles.question}>{m.question}</p>
                <div className={styles.answer}>
                  <p className={styles.meta}>
                    Argus · {momentLabel(m.t, span)}
                    {m.check_status === "fallback" && " · written by code"}
                  </p>
                  <p>{m.answer}</p>
                  {(m.body.chips ?? []).length > 0 && (
                    <div className={styles.chips} aria-label="Numbers this answer rests on">
                      {(m.body.chips ?? []).map((chip) => (
                        <EvidenceChip
                          key={chip.ref}
                          text={chip.display}
                          title={chipTitle(chip.label)}
                          t={chip.t}
                          vesselId={chip.vessel_id}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
        {busy && (
          <p className={styles.looking} role="status">
            Argus is looking…
          </p>
        )}
        <div ref={end} />
      </div>
      {!readOnly && messages !== null && showSuggestions(messages) && !busy && (
        <div className={styles.suggestions} aria-label="Suggested questions">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" className={styles.suggestion} onClick={() => ask(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
      {readOnly ? (
        <p className={styles.hint}>Ask your own questions in the app.</p>
      ) : (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault();
            ask(text);
          }}
        >
          <label className={styles.hidden} htmlFor={`chat-${runId}`}>
            Ask Argus about this moment
          </label>
          <textarea
            id={`chat-${runId}`}
            className={styles.input}
            value={text}
            rows={2}
            maxLength={MAX_QUESTION}
            placeholder={`Ask ${momentLabel(t, span)}…`}
            disabled={busy}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                ask(text);
              }
            }}
          />
          <button type="submit" className={styles.send} disabled={busy || cleanQuestion(text) === null}>
            Ask
          </button>
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
        </form>
      )}
    </div>
  );
}
