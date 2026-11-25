/**
 * Raid strategy docs (docs/strategy.md): officers add Google Docs to each classic raid, then each raid night pins the
 * docs its raiders see on the night's Raid page. Officers keep the docs in Google Drive; the hub only links them.
 * Nights are kept apart: a doc added through a night is that night's alone; a global officer's doc is shared.
 *
 * - GET    /api/strategy                  the raids' docs and nights' pins the caller may see
 * - POST   /api/admin/strategy            add a doc to a raid (global officers)
 * - DELETE /api/admin/strategy/{id}       take a doc down, off every night that pins it
 * - POST   /api/days/{day}/strategy/docs  add a doc as one of that night's officers
 * - DELETE /api/days/{day}/strategy/docs/{id}   take down one of the night's own docs
 * - GET    /api/days/{day}/strategy       the docs the night pins (the Raid page)
 * - PUT    /api/days/{day}/strategy       pin the night's docs, in order (that night's officers)
 */
import { ApiError, call, type Fetch } from "./api";

export const TITLE_LIMIT = 80;
export const URL_LIMIT = 500;
export const NIGHT_LIMIT = 10;

export interface Raid {
  id: string;
  short: string;
  name: string;
}

export interface StrategyDoc {
  id: number;
  raid: string;
  title: string;
  url: string;
  /** Who added it, by the name they chose on the hub; null once they are gone. */
  added_by: string | null;
  added_at: string;
}

export interface LibraryDoc extends StrategyDoc {
  /** The night it was added through, which alone sees and pins it; null: shared with every night. */
  night: string | null;
  /** The raid days that pin it for their raiders (only the nights the caller sees). */
  nights: string[];
}

export interface RaidDocs {
  raid: Raid;
  /** Newest first. */
  docs: LibraryDoc[];
}

export interface NightDocs {
  raid_day: string;
  name: string;
  /** Doc ids, in the order the Raid page lists them. */
  docs: number[];
}

export interface Library {
  raids: RaidDocs[];
  nights: NightDocs[];
}

export interface NightDoc {
  raid: Raid;
  doc: StrategyDoc;
}

export interface NightStrategy {
  raid_day: string;
  docs: NightDoc[];
}

export interface StrategyBackend {
  library(): Promise<Library>;
  /** `through`: the night the officer adds through; null for global officers and super admins. */
  add(
    raid: string,
    url: string,
    title: string,
    through: string | null,
  ): Promise<StrategyDoc>;
  remove(id: number, through: string | null): Promise<void>;
  night(day: string): Promise<NightStrategy>;
  setNight(day: string, docs: number[]): Promise<NightStrategy>;
}

const night = (day: string) => `/api/days/${encodeURIComponent(day)}/strategy`;
const docs = (day: string | null) =>
  day === null ? "/api/admin/strategy" : `${night(day)}/docs`;

export function hubStrategy(f: Fetch = fetch): StrategyBackend {
  return {
    library: () => call<Library>(f, "/api/strategy"),
    add: (raid, url, title, through) =>
      call<StrategyDoc>(f, docs(through), {
        method: "POST",
        body: JSON.stringify({ raid, url, title }),
      }),
    remove: (id, through) =>
      call<void>(f, `${docs(through)}/${encodeURIComponent(id)}`, {
        method: "DELETE",
      }),
    night: (day) => call<NightStrategy>(f, night(day)),
    setNight: (day, ids) =>
      call<NightStrategy>(f, night(day), {
        method: "PUT",
        body: JSON.stringify({ docs: ids }),
      }),
  };
}

/** The docs an officer can pin for `day`, as picker options: "ZG · Hakkar guide", raid by raid. A night pins its own
 * docs and the shared ones, never another night's. */
export function docOptions(
  library: Library,
  day: string,
): { id: string; short: string; name: string }[] {
  return library.raids.flatMap((r) =>
    r.docs.filter((d) => d.night === null || d.night === day).map((d) => ({
      id: String(d.id),
      short: r.raid.short,
      name: d.title,
    })),
  );
}

const GOOGLE_HOSTS = new Set(["docs.google.com", "drive.google.com"]);

/** The API's own check, so the form can say what is wrong before sending: an https Google Docs or Drive link. */
export function docProblem(url: string, title = ""): string | null {
  if (title.trim().length > TITLE_LIMIT)
    return `Keep the name to ${TITLE_LIMIT} characters.`;
  const text = url.trim();
  if (!text) return "Paste the Google Doc’s link.";
  try {
    const u = new URL(text);
    if (
      u.protocol !== "https:" ||
      !GOOGLE_HOSTS.has(u.hostname) ||
      u.username ||
      u.password
    )
      throw new Error("host");
    if (text.length > URL_LIMIT || /\s/.test(text)) throw new Error("shape");
  } catch {
    return "Paste the doc’s https://docs.google.com or drive.google.com link.";
  }
  return null;
}

/** "Added 22 Oct by Hopscotch". */
export function addedLine(
  doc: Pick<StrategyDoc, "added_at" | "added_by">,
): string {
  const when = new Date(doc.added_at).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
  return doc.added_by ? `Added ${when} by ${doc.added_by}` : `Added ${when}`;
}

export function strategyError(e: unknown): string {
  if (!(e instanceof ApiError)) return "Something went wrong; try again.";
  if (e.status === 403)
    return e.message && e.message !== "Forbidden"
      ? e.message
      : "Only officers add strategy docs, and only a night’s officers pin its docs.";
  if (e.status === 404)
    return "That doc is gone; someone may have taken it down.";
  return e.message || "Something went wrong; try again.";
}
