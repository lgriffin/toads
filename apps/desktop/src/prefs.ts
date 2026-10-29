/** The app's own settings and window position, kept as small JSON files in the app's user data folder. */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

export interface Prefs {
  /** Closing the window keeps the app in the tray, so desk notifications keep coming. */
  keepInTray: boolean;
  /** Native notifications when new work reaches an officer's desk. */
  deskNotifications: boolean;
}

export const DEFAULT_PREFS: Prefs = { keepInTray: false, deskNotifications: true };

export function parsePrefs(body: unknown): Prefs {
  const p = body && typeof body === 'object' ? (body as Record<string, unknown>) : {};
  return {
    keepInTray: typeof p.keepInTray === 'boolean' ? p.keepInTray : DEFAULT_PREFS.keepInTray,
    deskNotifications: typeof p.deskNotifications === 'boolean' ? p.deskNotifications : DEFAULT_PREFS.deskNotifications
  };
}

/** A JSON file in `dir`: missing or unreadable reads as undefined, so a corrupt file falls back to the defaults. */
export function jsonFile(dir: string, name: string) {
  const path = join(dir, name);
  return {
    read(): unknown {
      try {
        return JSON.parse(readFileSync(path, 'utf-8'));
      } catch {
        return undefined;
      }
    },
    write(value: unknown): void {
      try {
        writeFileSync(path, JSON.stringify(value, null, 2));
      } catch {
        // A read-only or full disk only costs the remembered setting.
      }
    }
  };
}
