# Recruitment: raid nights and interview panels

Applicants pick the night they want to raid (Wednesday, Thursday or Sunday) on the `/recruit` page. The choices
are the raid days in `config/raid_days.yaml`, so a new night shows up once it is configured, with no code change. Each night's
officers choose that night's interview panel from the members of the Toads Discord on **Officers > Recruitment**
(`/officers/recruitment`). When someone applies for Sunday, the Toad Bot opens their private interview room straight
away with the applicant, the Sunday panel and the bot in it, and posts their answers there.

## Who interviews whom

1. The panel of the night the applicant chose.
2. If that night has no panel yet (or the application names no night, as from an older client), the `interviewers`
   list in `config/community.yaml`, as before.
3. If both are empty, nobody is added automatically: the application waits as **Applied** until an officer opens the
   room from the officer console, and the officers of the nights applied for (plus the global tier) are let in.

The API accepts more than one night in `raid_days`; the room then gets every chosen night's panel. The recruit page
sends exactly one.

## Who sets a panel

That night's officers, global officers and super admins (`MANAGE_RECRUITMENT`, scoped to the raid day in the URL).
The other night's officers cannot see or change it (403). Global officers and super admins see a card for every night.

- Search finds members of the Toads Discord whose username or server nickname starts with what you type. They do not
  need to have signed in to the hub.
- A panel holds at most 10 people. Adding someone checks they are still in the server; adding them twice is refused.
- The panel stores each person's Discord user id, so a renamed account keeps its place. The name shown is their server
  name when they were added.
- Every change is on the audit log: `recruitment.panel_add` and `recruitment.panel_remove`, with the raid day.
- A change applies to the next application. Rooms that are already open keep the people they were opened with.

## When a room does not open

The recruit page waits for the Toad Bot after someone applies. Once the room exists it shows **Open your interview
room**, a link straight into it (`https://discord.com/channels/<server>/<room>`, built by the API from
`TOADS_DISCORD_GUILD_ID`). It never links to the invite: an invite drops a member in whichever channel it was made for.

If the bot cannot open the room for a reason retrying will not fix, it says why and the hub keeps that on the
application as `interview_room_error` (migration 0025). The applicant sees it on the page; officers see it in
`GET /api/.../admin/applications`, and asking for the room again (`POST .../interview-room`) clears it. The reasons:

- `The Toad Bot needs Manage Channels, Manage Roles in the Interviews category` (or `in the server`): grant them
  (ADMIN_GUIDE "Discord permissions for interview rooms").
- `The applicant is no longer in the Discord server`.
- `Discord refused: ...`: Discord's own error, such as 403 Missing Permissions, or a full category (Discord allows
  50 channels in one).

A Discord outage or rate limit is not a reason: the job stays in the outbox and the next poll (every 30 seconds) tries
again. The bot logs everything else, starting with a check at startup:

```bash
cd /opt/toads && sudo -u toads docker compose -f infra/docker-compose.prod.yml logs --since 1h bot
```

| Bot log line | Meaning |
| --- | --- |
| `the Toad Bot is in Toads and can open interview rooms` | Startup check passed |
| `the Toad Bot is not in server ... (TOADS_DISCORD_GUILD_ID)` | Wrong server id in `services/bot/.env`, or the bot was never invited |
| `the Toad Bot needs ... to open interview rooms` | Missing permissions, server-wide |
| `cannot read the hub's outbox at ...` | `TOADS_HUB_API_URL` or `TOADS_HUB_SERVICE_TOKEN` in `services/bot/.env` is wrong, or the API is down |
| `interview_category_id ... is not a category` | Fix the id in `config/community.yaml`; rooms open at the top of the channel list until then |
| `outbox job ... failed: ...` | The reason above, also shown on the application |

## API

- `GET /api/public/raid-nights`: the nights the recruit page offers, `[{id, name}]` in `config/raid_days.yaml` order.
- `GET /api/days/{day}/admin/interview-panel`: `{raid_day, interviewers: [{discord_user_id, username,
  display_name}], fallback}`; `fallback` is the community config's `interviewers`, who step in while the panel is
  empty. Discord ids are strings, since they are past what a browser can hold as a number.
- `GET /api/days/{day}/admin/discord-members?q=`: up to 10 server members matching `q` (1 to 32 characters).
- `POST /api/days/{day}/admin/interview-panel` with `{discord_user_id}`: add someone (201 with the panel; 409 if they
  are already on it or it is full; 422 if they are not in the server; 503 if Discord does not answer).
- `DELETE /api/days/{day}/admin/interview-panel/{discord_user_id}`: take someone off (404 if they are not on it).

Panels live in the hub database's `interview_panelists` table (migration 0021). The member search uses Discord's
`GET /guilds/{id}/members/search` with the bot token, which needs the Toad Bot's **Server Members** intent, already on
for interview rooms (ADMIN_GUIDE "Discord permissions for interview rooms").
