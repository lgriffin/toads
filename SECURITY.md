# Security

The hub holds a Warcraft Logs client secret, a Discord bot token and images uploaded by guild members.

## Reporting

If you find a problem, message Leigh on the Toads Discord or open a private security advisory on this
repository. Please do not post details in public channels.

## Controls

The Security table in the Toads Hub build spec is the source of truth; every control there has a test
marked `@pytest.mark.security`, run in its own CI job. In short:

- Discord OAuth2 with PKCE is the only login; roles come from Discord, never from the client.
- Sessions are opaque ids in Redis, HttpOnly + Secure + SameSite=Lax, revocable server-side.
- Secrets arrive only through environment variables, are typed `SecretStr`, and never appear in logs,
  errors or validation responses. gitleaks runs on every PR.
- Report codes must match `^[A-Za-z0-9]{16}$` before any request; SQL goes through SQLAlchemy.
- Uploads use presigned PUTs to a private bucket, magic-byte checks, EXIF stripping and WebP re-encoding.
- Dependencies are locked (`uv.lock`, `package-lock.json`) and audited in CI.
