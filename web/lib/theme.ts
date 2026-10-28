// Theme choice: "system" follows prefers-color-scheme (no data-theme attribute);
// "light" and "dark" set data-theme on <html>. The choice is kept in localStorage when it is available.

export type ThemeChoice = "system" | "light" | "dark";

export const THEME_KEY = "argus-theme";

// Runs in <head> before first paint so a saved choice never flashes the other theme.
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;

const listeners = new Set<() => void>();
let chosen: ThemeChoice | null = null; // survives when storage is blocked

function stored(): ThemeChoice {
  try {
    const value = localStorage.getItem(THEME_KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

function setAttribute(choice: ThemeChoice) {
  if (choice === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", choice);
}

export function readTheme(): ThemeChoice {
  return chosen ?? stored();
}

export function setTheme(choice: ThemeChoice) {
  chosen = choice;
  setAttribute(choice);
  try {
    if (choice === "system") localStorage.removeItem(THEME_KEY);
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
