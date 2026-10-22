# Highlights: photos, streams and clips

The Highlights page (`/highlights`) is raid night in pictures. Members fill it from Discord with the Toad Bot:

| Command | What it does | Who |
| --- | --- | --- |
| `/highlight photo:<file> [caption]` | Posts a photo: once approved, 48 hours in the carousel, then the archive for good | raiders (any night), officers |
| `/stream start link:<twitch link> [title]` | Shows the member's Twitch channel in **Live now**, and says so in the channel (once the channel is approved) | raiders, officers |
| `/stream end` | Takes their stream off the page | raiders, officers |
| `/clip link:<url> title:<text>` | Shares a YouTube, Twitch clip or Streamable link for review | raiders, officers |

Everything here is members-only (`view_guild_raids` to look), and nothing shows until an officer approves it (see
**Approval** below). Nothing reaches the public Story unless a global officer publishes a clip to it.

```
 raider ──/highlight, /stream, /clip──▶ Toad Bot ──POST /api/gallery/… or /api/highlights (hub token, acting member)──▶ hub API
 member ──/highlights──▶ GET /api/gallery/board, /photos, /photos/{id}/image|thumbnail, GET /api/highlights
 global officer ──/highlights──▶ photo of the week, take-downs, clip review
```

The Toad Bot calls with `TOADS_HUB_SERVICE_TOKEN` and `X-Toads-Acting-Member`; the hub reads the member's roles from
Discord, as for `/bankrequest`, so the bot can do nothing the member could not. Those routes are listed in
`TOAD_BOT_ACTING_PATHS` (`rbac/deps.py`); taking things down, picking the photo of the week and reviewing clips stay on
the site.

## Approval

Photos and streams wait for an officer before anyone else sees them, so spam or anything unsuitable never reaches the
page.

- **Who decides.** A raid night's officers decide what members of their night post (the poster's night roles at their
  last sign-in, `members.raid_days`); global officers decide anyone's, including members on no night. A poster on two
  nights can be decided by either night's officers.
- **Where.** "Waiting for your approval" at the top of the Highlights page, for anyone who can decide something. Night
  officers' calls go to `/api/days/{day}/gallery/...` (the night from the path, as for claims), global officers' to
  `/api/admin/gallery/...`.
- **Photos.** Approve puts it in the carousel for 48 hours from the approval, then the archive. Turn down deletes it and
  its bytes for good. While it waits, only its poster (under "Waiting for an officer") and the officers who may decide it
  can open it; the Toad Bot tells the poster it is with the officers.
- **Streams.** The first stream from a channel waits, and the bot does not announce it. Approving it puts it in **Live
  now** and trusts that channel for that member (`gallery_trusted_channels`), so their later streams from it go up and
  are announced at once. Turning one down ends it. An officer taking down a stream withdraws the trust, so the next one
  waits again.
- Every approval and rejection is on the audit log (`gallery.approve_photo`, `gallery.reject_photo`,
  `gallery.approve_stream`, `gallery.reject_stream`). Photos and streams already up before approval existed (migration
  `0039`) count as approved.

## Photos

- **Posting** needs `upload_screenshots` (raiders and up). A photo is JPEG, PNG, WebP or a still GIF, up to 10 MB and 50
  megapixels; animated images and other formats are refused with the reason. A member can post 20 a day.
- **Re-encoding.** The hub never keeps the file as sent: Pillow decodes it, turns it the right way up, and writes a WebP
  of at most 2048 px and a 640 px thumbnail. EXIF is dropped, so a phone photo's GPS position never reaches the page.
  The bytes live in Postgres (`gallery_photo_files`, migration `0036`), so the nightly backup holds them.
- **Carousel and archive.** The carousel shows photos approved in the last 48 hours, newest first. The archive lists every
  approved photo, by month, 48 at a time. Nothing expires out of the archive.
- **Photo of the week.** A global officer opens any approved photo and picks it; it sits at the top of the page for seven days.
  A new pick ends the running one. Every pick is kept (`photo_of_the_week`) and marked in the archive.
- **Taking down.** The member who posted a photo, or a global officer, can take it down from the page. That deletes it
  and its bytes for good and records `gallery.remove_photo` on the audit log.

## Streams

`/stream start` keeps only the Twitch login from the link (`twitch.tv/<name>`; anything else is refused), and the page
builds the player URL itself (`player.twitch.tv`, allowed in the CSP's `frame-src`). The player loads when a member
presses Watch, then plays muted in the page for as long as the stream runs. One stream per member: starting again
replaces the last.

A stream leaves the page when its member runs `/stream end`, a global officer takes it off, or 12 hours pass. With a
Twitch application configured (`TOADS_TWITCH_CLIENT_ID` and `TOADS_TWITCH_CLIENT_SECRET` on the API; create one at
https://dev.twitch.tv/console, no redirect needed), the page also shows a stream only while Twitch lists the channel as
live, checking at most once a minute. A stream started in the last five minutes always shows, since Twitch takes a moment
to list it. If Twitch does not answer, every open stream shows.

## Clips

`/clip` goes through the community layer's highlight reels (REQ-HUB-SPOT-001/002): only https YouTube, Twitch clip or
Streamable links, stored as provider and clip id, held until a global officer publishes them to members, to the Story
too, or turns them down. Global officers review them in the Clips section of the Highlights page. Clips load from their
provider only when someone presses play.

## Routes

| Route | Permission |
| --- | --- |
| `GET /api/gallery/board` | `view_guild_raids` |
| `GET /api/gallery/photos?before=&limit=` | `view_guild_raids` |
| `GET /api/gallery/photos-of-the-week` | `view_guild_raids` |
| `GET /api/gallery/photos/{id}/image`, `/thumbnail` | `view_guild_raids`; a waiting photo only its poster and its officers |
| `POST /api/gallery/photos` (`{caption, image_base64}`) | `upload_screenshots` |
| `DELETE /api/gallery/photos/{id}` | `view_guild_raids`, and its poster or `manage_highlights` |
| `POST /api/admin/gallery/photos/{id}/photo-of-the-week` | `manage_highlights` (global tier) |
| `POST /api/gallery/streams` (`{link, title}`), `POST /api/gallery/streams/end` | `submit_highlight` |
| `DELETE /api/gallery/streams/{id}` | `view_guild_raids`, and its streamer or `manage_highlights` |
| `GET /api/days/{day}/gallery/review` | `manage_highlights` on that night |
| `POST /api/days/{day}/gallery/photos/{id}/approve`, `/reject`, `.../streams/{id}/approve`, `/reject` | `manage_highlights` on that night, for a poster on it |
| `GET /api/admin/gallery/review` | `manage_highlights` (global tier) |
| `POST /api/admin/gallery/photos/{id}/approve`, `/reject`, `.../streams/{id}/approve`, `/reject` | `manage_highlights` (global tier) |

The rules are in `toads_api.gallery.service` over the `GalleryRepository` protocol (`sql.py` over hub-db,
`InMemoryGalleryRepository` for tests); requirements are REQ-HUB-GALLERY-001..012 in `tests/features/hub_gallery.feature`.
