# Security

The hub holds a Warcraft Logs client secret, a Discord bot token and images uploaded by guild members.

## Reporting

If you find a problem, message Leigh on the Toads Discord or open a private security advisory on this
repository. Please do not post details in public channels.

## Controls

The Security table in the Toads Hub build spec is the source of truth; every control there has a test
marked `@pytest.mark.security`, run in its own CI job. In short:

- Discord OAuth2 with PKCE is the only login; roles come from Discord, never from the client.
- Login state and the PKCE verifier are bound to a short-lived pre-auth cookie and used once; a replayed
  or mismatched state is refused.
- Sessions are opaque ids in Redis (stored as SHA-256 digests), HttpOnly + Secure + SameSite=Lax,
  revocable server-side. Discord roles are re-read at least every 15 minutes; losing a mapped role,
  leaving the server or revoking the app ends the session. If Discord cannot be reached at refresh time
  the request fails closed (503) rather than trusting stale roles.
- An officer's attempt to reach a sibling raid day's officer view or data is refused and audited.
- Secrets arrive only through environment variables, are typed `SecretStr`, and never appear in logs,
  errors or validation responses. gitleaks runs on every PR.
- Report codes must match `^[A-Za-z0-9]{16}$` before any request; SQL goes through SQLAlchemy.
- Uploads use presigned PUTs to a private bucket, magic-byte checks, EXIF stripping and WebP re-encoding.
- Dependencies are locked (`uv.lock`, `package-lock.json`) and audited in CI.
