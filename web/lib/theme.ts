// Theme choice (D-98): light, the clean-lab look, is the default and needs no attribute; "dark" and "system" (follow
// prefers-color-scheme) set data-theme on <html>. The choice is kept in localStorage when it is available.

export type ThemeChoice = "system" | "light" | "dark";

export const THEME_KEY = "argus-theme";

// Runs in <head> before first paint so a saved choice never flashes the other theme.
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_KEY}");if(t==="dark"||t==="system")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;

const listeners = new Set<() => void>();
let chosen: ThemeChoice | null = null; // survives when storage is blocked

function stored(): ThemeChoice {
  try {
    const value = localStorage.getItem(THEME_KEY);
    return value === "dark" || value === "system" ? value : "light";
  } catch {
    return "light";
  }
}

function setAttribute(choice: ThemeChoice) {
  if (choice === "light") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", choice);
}

export function readTheme(): ThemeChoice {
  return chosen ?? stored();
}

export function setTheme(choice: ThemeChoice) {
  chosen = choice;
  setAttribute(choice);
  try {
    if (choice === "light") localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, choice);
  } catch {
    // Private windows and blocked storage: the choice lasts for this page only.
  }
  listeners.forEach((listener) => listener());
}

export function subscribeTheme(listener: () => void): () => void {
  const onStorage = (event: StorageEvent) => {
    if (event.key !== THEME_KEY) return;
    chosen = null;
    setAttribute(stored());
    listener();
  };
  listeners.add(listener);
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}
