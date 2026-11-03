// Ask Argus (D-97): the small pure pieces of the chat panel.
import { formatRunTime } from "./scale.ts";
import type { ChatMessage } from "./types.ts";

export const MAX_QUESTION = 500; // the worker refuses longer questions (argus/api/chat.py)

export const SUGGESTIONS = [
  "What's happening now?",
  "Which sample is changing the most?",
  "Can Argus judge the idea yet?",
] as const;

/** The moment an answer is about, as the run's clock reads it: "about 4:12". */
export function momentLabel(t: number, span: number): string {
  return `about ${formatRunTime(t, span)}`;
}

/** The question as it will be sent, or null when there is nothing to send or it is too long. */
export function cleanQuestion(text: string): string | null {
  const question = text.trim();
  return question.length === 0 || question.length > MAX_QUESTION ? null : question;
}

/** Suggested questions help start a conversation; once it has started they step aside. */
export function showSuggestions(messages: ChatMessage[]): boolean {
  return messages.length === 0;
}
