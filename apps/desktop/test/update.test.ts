import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { Offers, RELEASES, TAG_PREFIX, downloadPrompt, readyPrompt, releasePage, updateMode } from '../src/update';

const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const workflow = readFileSync(new URL('../../../.github/workflows/desktop.yml', import.meta.url), 'utf8');

describe('updates without a reinstall', () => {
  it('installs updates itself everywhere but on an unsigned Mac, where it links the release instead', () => {
    expect(updateMode('win32', false)).toBe('install');
    expect(updateMode('linux', false)).toBe('install');
    expect(updateMode('darwin', true)).toBe('install');
    expect(updateMode('darwin', false)).toBe('notify');
  });

  it("links a version's release page by the workflow's tag", () => {
    expect(releasePage('0.2.0')).toBe('https://github.com/lgriffin/toads/releases/tag/desktop-v0.2.0');
    expect(workflow).toContain(`tags: ["${TAG_PREFIX}*"]`);
  });

  it('offers each version once, a newer one again, and everything again after a check the reader asked for', () => {
    const offers = new Offers();
    expect(offers.shouldOffer('0.2.0')).toBe(true);
    expect(offers.shouldOffer('0.2.0')).toBe(false);
    expect(offers.shouldOffer('0.3.0')).toBe(true);
    offers.forget();
    expect(offers.shouldOffer('0.3.0')).toBe(true);
  });

  it('asks to restart into a downloaded update, or to download one on a Mac', () => {
    expect(readyPrompt('0.2.0', '0.1.0')).toMatchObject({ message: 'Toads Hub 0.2.0 is ready', buttons: ['Restart now', 'Later'] });
    expect(downloadPrompt('0.2.0', '0.1.0').buttons[0]).toBe('Open release page');
  });
});

describe('the release carries the update feeds', () => {
  it('builds them for the repository the app reads releases from', () => {
    const [publish] = pkg.build.publish;
    expect(`https://github.com/${publish.owner}/${publish.repo}/releases`).toBe(RELEASES);
    expect(publish).toMatchObject({ provider: 'github', releaseType: 'release' });
    expect(pkg.dependencies).toHaveProperty('electron-updater');
  });

  it('builds the Mac zip that Squirrel.Mac installs from, beside the dmg people download', () => {
    const targets = pkg.build.mac.target.map((t: { target: string }) => t.target);
    expect(targets).toEqual(expect.arrayContaining(['dmg', 'zip']));
  });

  it('publishes the feeds, blockmaps and Mac zips with the installers', () => {
    for (const file of ['release/latest*.yml', 'release/*.blockmap', 'release/*.zip']) {
      expect(workflow).toContain(`apps/desktop/${file}`);
    }
  });
});
