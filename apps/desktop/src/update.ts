/**
 * Updates without a reinstall (docs/desktop.md#updates, REQ-HUB-APP-007). Each `desktop-v<version>` release carries
 * electron-builder's update feeds (latest.yml, latest-mac.yml, latest-linux.yml); the installed app reads them from the
 * latest GitHub release, downloads a newer version in the background and installs it on restart.
 *
 * macOS is the exception while the app is unsigned: Squirrel.Mac installs an update only when it is signed by the same
 * Developer ID as the running app, which an ad-hoc signature can never be. There the app says a new version is out and
 * opens its release page instead.
 */

/** Where the release pages live; electron-builder's `publish` setting in package.json names the same repository. */
export const RELEASES = 'https://github.com/lgriffin/toads/releases';
export const TAG_PREFIX = 'desktop-v';

/** The first check waits for the hub to load; after that, a few times a day for an app left running in the tray. */
export const FIRST_CHECK_MS = 30 * 1000;
export const CHECK_EVERY_MS = 6 * 60 * 60 * 1000;

/** 'install': download in the background and install on restart. 'notify': say it is out and link the release. */
export type UpdateMode = 'install' | 'notify';

export function updateMode(platform: NodeJS.Platform, macSigned: boolean): UpdateMode {
  return platform === 'darwin' && !macSigned ? 'notify' : 'install';
}

export function releasePage(version: string): string {
  return `${RELEASES}/tag/${TAG_PREFIX}${encodeURIComponent(version)}`;
}

/**
 * Offer each new version once: a reader who chose Later is not asked again at every check (a downloaded update is
 * reported again each time), but a newer release asks, and so does a check they ask for themselves (`forget`).
 */
export class Offers {
  private readonly offered = new Set<string>();

  shouldOffer(version: string): boolean {
    if (this.offered.has(version)) return false;
    this.offered.add(version);
    return true;
  }

  forget(): void {
    this.offered.clear();
  }
}

export interface Prompt {
  message: string;
  detail: string;
  buttons: [string, string];
}

/** An update has downloaded: restart into it now, or let it install the next time the app quits. */
export function readyPrompt(version: string, current: string): Prompt {
  return {
    message: `Toads Hub ${version} is ready`,
    detail: `You have ${current}. Restart to finish updating, or it will update the next time you quit the app.`,
    buttons: ['Restart now', 'Later']
  };
}

/** A newer version is out, on a Mac build that cannot install it by itself. */
export function downloadPrompt(version: string, current: string): Prompt {
  return {
    message: `Toads Hub ${version} is out`,
    detail: `You have ${current}. Download the new version from its release page and drag it into Applications.`,
    buttons: ['Open release page', 'Later']
  };
}
