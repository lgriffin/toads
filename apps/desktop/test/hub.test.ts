import { describe, expect, it } from 'vitest';
import { LIVE_HUB, hubOrigin, hubUrl, resolveHub } from '../src/hub';

describe('hubOrigin', () => {
  it('takes any https hub and plain http only to this machine', () => {
    expect(hubOrigin('https://toads.gg/hub')).toBe('https://toads.gg');
    expect(hubOrigin('https://staging.toads.gg:8443')).toBe('https://staging.toads.gg:8443');
    expect(hubOrigin('http://localhost:8080')).toBe('http://localhost:8080');
    expect(hubOrigin('http://127.0.0.1:8080/x')).toBe('http://127.0.0.1:8080');
    expect(hubOrigin('http://[::1]:8080')).toBe('http://[::1]:8080');
  });

  it('refuses plain http elsewhere, other schemes, credentials and junk', () => {
    expect(hubOrigin('http://toads.gg')).toBeNull();
    expect(hubOrigin('file:///etc/passwd')).toBeNull();
    expect(hubOrigin('javascript:alert(1)')).toBeNull();
    expect(hubOrigin('https://user:pw@toads.gg')).toBeNull();
    expect(hubOrigin('toads.gg')).toBeNull();
  });
});

describe('resolveHub', () => {
  it('opens the live hub by default', () => {
    expect(resolveHub([], {})).toBe(LIVE_HUB);
  });

  it('puts --hub before TOADS_HUB_URL', () => {
    expect(resolveHub(['electron', '--hub=http://localhost:8080'], { TOADS_HUB_URL: 'https://staging.toads.gg' })).toBe(
      'http://localhost:8080'
    );
    expect(resolveHub([], { TOADS_HUB_URL: 'https://staging.toads.gg' })).toBe('https://staging.toads.gg');
  });

  it('fails on a bad override instead of quietly opening another hub', () => {
    expect(() => resolveHub(['--hub=http://evil.example'], {})).toThrow(/https, or http to localhost/);
  });
});

it('hubUrl joins a path onto the hub', () => {
  expect(hubUrl('https://toads.gg', '/officers/claims')).toBe('https://toads.gg/officers/claims');
});
