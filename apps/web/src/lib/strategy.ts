/**
 * Raid strategy docs (docs/strategy.md): Google Docs pinned to classic raids, for every night or for one night, and the
 * raids each night is running, so the night's Raid page shows each raid's doc. Officers keep the docs in Google Drive;
 * the hub only links them.
 *
 * - GET    /api/strategy                  every raid's docs, for every night and each night's own, and each night's raids
 * - POST   /api/admin/strategy            pin a doc to a raid for every night or one night (global officers)
 * - DELETE /api/admin/strategy/{id}       take a doc down; the one it replaced is pinned again
 * - POST   /api/days/{day}/strategy/docs  pin as one of that night's officers, for that night or every night
 * - DELETE /api/days/{day}/strategy/docs/{id}
 * - GET    /api/days/{day}/strategy       the raids the night is running, each with its doc (the Raid page)
 * - PUT    /api/days/{day}/strategy       say which raids the night is running, in order (that night's officers)
 */
import { ApiError, call, type Fetch } from "./api";

export const TITLE_LIMIT = 80;
export const URL_LIMIT = 500;

export interface Raid {
  id: string;
  short: string;
  name: string;
}

export interface StrategyDoc {
  id: number;
  raid: string;
  /** The night it is pinned for; null for every night. */
  raid_day: string | null;
  title: string;
  url: string;
  /** Who pinned it, by the name they chose on the hub; null once they are gone. */
  added_by: string | null;
  added_at: string;
}

/** A raid's docs for one night, or for every night (`raid_day` null). */
export interface Slot {
  raid_day: string | null;
  /** "Every night", or the night's name. */
  name: string;
  pinned: StrategyDoc;
  /** The docs the pinned one replaced, newest first. */
  replaced: StrategyDoc[];
}

export interface RaidStrategy {
  raid: Raid;
  /** Every night's doc first, then each night's own; only where a doc is pinned. */
  slots: Slot[];
}

export interface NightRaids {
  raid_day: string;
  name: string;
  /** Raid ids, in the order the night runs them. */
  raids: string[];
}

export interface Library {
  raids: RaidStrategy[];
  nights: NightRaids[];
}

export interface NightRaidDoc {
  raid: Raid;
  /** The night's own doc for the raid, else its every-night doc. */
  pinned: StrategyDoc | null;
}

export interface NightStrategy {
  raid_day: string;
  raids: NightRaidDoc[];
}

/**
 * Where a doc is pinned from. `through`: the night the officer pins through (null for global officers and super
 * admins). `night`: the night the doc is for (null for every night).
 */
export interface PinTarget {
  through: string | null;
  night: string | null;
}

export interface StrategyBackend {
  library(): Promise<Library>;
  pin(
    raid: string,
    url: string,
    title: string,
    target: PinTarget,
  ): Promise<StrategyDoc>;
  /** `through`: the night the officer takes it down through; null for the global tier. */
  remove(id: number, through: string | null): Promise<void>;
  night(day: string): Promise<NightStrategy>;
  setNight(day: string, raids: string[]): Promise<NightStrategy>;
}

const night = (day: string) => `/api/days/${encodeURIComponent(day)}/strategy`;
const docs = (day: string | null) =>
  day === null ? "/api/admin/strategy" : `${night(day)}/docs`;

function pinBody(
  raid: string,
  url: string,
  title: string,
  { through, night }: PinTarget,
) {
  if (through === null) return { raid, url, title, raid_day: night };
  return { raid, url, title, every_night: night === null };
}

export function hubStrategy(f: Fetch = fetch): StrategyBackend {
  return {
    library: () => call<Library>(f, "/api/strategy"),
    pin: (raid, url, title, target) =>
      call<StrategyDoc>(f, docs(target.through), {
        method: "POST",
        body: JSON.stringify(pinBody(raid, url, title, target)),
      }),
    remove: (id, through) =>
      call<void>(f, `${docs(through)}/${encodeURIComponent(id)}`, {
        method: "DELETE",
      }),
    night: (day) => call<NightStrategy>(f, night(day)),
    setNight: (day, raids) =>
      call<NightStrategy>(f, night(day), {
        method: "PUT",
        body: JSON.stringify({ raids }),
      }),
  };
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

/** "Pinned 22 Oct by Hopscotch". */
export function pinnedLine(
  doc: Pick<StrategyDoc, "added_at" | "added_by">,
): string {
  const when = new Date(doc.added_at).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
  return doc.added_by ? `Pinned ${when} by ${doc.added_by}` : `Pinned ${when}`;
}

export function strategyError(e: unknown): string {
  if (!(e instanceof ApiError)) return "Something went wrong; try again.";
  if (e.status === 403)
    return "Only officers pin strategy docs, and only a night’s officers pick its raids.";
  if (e.status === 404)
    return "That doc is gone; someone may have taken it down.";
  return e.message || "Something went wrong; try again.";
}
