import { describe, expect, it } from 'vitest';
import { destination, isDiscordSignIn, permissionAllowed } from '../src/links';

const HUB = 'https://toads.gg';

describe('destination', () => {
  it('keeps the hub in the window', () => {
    expect(destination('https://toads.gg/officers/claims', HUB)).toBe('app');
    expect(destination('https://toads.gg/auth/callback?code=x&state=y', HUB)).toBe('app');
  });

  it("keeps Discord's sign-in pages in the window so the session cookie comes back to it", () => {
    expect(destination('https://discord.com/oauth2/authorize?client_id=1', HUB)).toBe('app');
    expect(destination('https://discord.com/login?redirect_to=%2Foauth2%2Fauthorize', HUB)).toBe('app');
    expect(destination('https://discord.com/register', HUB)).toBe('app');
  });

  it('sends every other site, and the rest of Discord, to the browser', () => {
    expect(destination('https://docs.google.com/document/d/x', HUB)).toBe('browser');
    expect(destination('https://www.warcraftlogs.com/reports/abc', HUB)).toBe('browser');
    expect(destination('https://discord.com/channels/1/2', HUB)).toBe('browser');
    expect(destination('https://discord.gg/toads', HUB)).toBe('browser');
    expect(destination('mailto:officers@toads.gg', HUB)).toBe('browser');
    expect(destination('discord://discord.com/channels/1/2', HUB)).toBe('browser');
  });

  it('treats a look-alike host or another port as another site', () => {
    expect(destination('https://toads.gg.example.com/hub', HUB)).toBe('browser');
    expect(destination('https://toads.gg:8443/hub', HUB)).toBe('browser');
    expect(destination('http://toads.gg/hub', HUB)).toBe('browser');
    expect(destination('https://evil.example/oauth2/authorize', HUB)).toBe('browser');
  });

  it('opens nothing else', () => {
    expect(destination('file:///etc/passwd', HUB)).toBe('blocked');
    expect(destination('javascript:alert(1)', HUB)).toBe('blocked');
    expect(destination('smb://server/share', HUB)).toBe('blocked');
    expect(destination('https://user:pw@example.com', HUB)).toBe('blocked');
    expect(destination('not a url', HUB)).toBe('blocked');
  });
});

it('isDiscordSignIn needs https on discord.com', () => {
  expect(isDiscordSignIn('http://discord.com/oauth2/authorize')).toBe(false);
  expect(isDiscordSignIn('https://discord.com/oauth2/authorized-apps')).toBe(false);
  expect(isDiscordSignIn('https://www.discord.com/login')).toBe(true);
  expect(isDiscordSignIn('nope')).toBe(false);
});

describe('permissionAllowed', () => {
  it("gives the hub's pages notifications and clipboard writes only", () => {
    expect(permissionAllowed('notifications', 'https://toads.gg/hub', HUB)).toBe(true);
    expect(permissionAllowed('clipboard-sanitized-write', 'https://toads.gg', HUB)).toBe(true);
    expect(permissionAllowed('notifications', 'https://discord.com/login', HUB)).toBe(false);
    expect(permissionAllowed('notifications', 'garbage', HUB)).toBe(false);
  });

  it('lets embedded clips go fullscreen', () => {
    expect(permissionAllowed('fullscreen', 'https://www.youtube-nocookie.com/embed/x', HUB)).toBe(true);
  });

  it('refuses camera, microphone, location and the rest, even to the hub', () => {
    for (const p of ['media', 'geolocation', 'midi', 'hid', 'usb', 'serial', 'openExternal', 'pointerLock']) {
      expect(permissionAllowed(p, 'https://toads.gg/hub', HUB)).toBe(false);
    }
  });
});
