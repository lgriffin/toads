# Discord bots, bound both ways to the hub

A reusable way to build Discord bots that talk to the site in both directions. It covers the shape only: bots
authenticate with the shared service token, and there is no per-member permission model yet (see "Not yet" below).

```
 site feature ──send(bot, kind, payload)──▶ BotBridge ◀──GET  /api/bots/{bot}/actions──────── ActionRunner ─▶ Binding ─▶ Discord
      ▲                                      │  ▲      ◀──POST /api/bots/{bot}/actions/{id}/result   (refs: message_id, …)
      └──── on_result / on_event listeners ◀─┘  └──────◀──POST /api/bots/{bot}/events ◀──── Binding.emit ◀── Discord listener
```

## Pieces

| Where | What |
| --- | --- |
| `services/bot/src/toads_bot/kit/spec.py` | `BotSpec` (a name and its bindings), `KitSettings`, `build_bot` |
| `services/bot/src/toads_bot/kit/binding.py` | `Binding`, a cog that declares `site_actions` (kind to method) and `discord_events`, and calls `emit` |
| `services/bot/src/toads_bot/kit/runner.py` | `ActionRunner`: pulls a bot's actions, runs each handler, reports the result |
| `services/bot/src/toads_bot/kit/link.py` | `HubLink` protocol and `HttpHubLink`, the bot's only door into the hub |
| `services/bot/src/toads_bot/kit/gate.py` | `Gate` protocol; `OpenGate` lets everyone do everything for now |
| `services/bot/src/toads_bot/kit/relay.py` | `Relay`, the example binding: `say` out, `message` in |
| `services/bot/src/toads_bot/kit/bank.py` | `Bank`, the guild bank: `bank.dm` and `bank.post` out, `/bank` commands and buttons ([bank.md](bank.md)) |
| `services/bot/src/toads_bot/kit/specs.py` | `SPECS`, every bot this repo can run |
| `services/api/src/toads_api/bots/bridge.py` | `BotBridge`: registry, action queue with retries, event dedup and listeners |
| `services/api/src/toads_api/bots/routes.py` | `/api/bots/*` routes, service token only |

The wire models live in `toads_api.bots.models` and, as a copy, in `toads_bot.kit.contract`. The bot may not import
`toads_api`, so `tests/test_bot_contract.py` checks that both copies describe the same JSON.

## The bots

| Spec | Bindings | What it does |
| --- | --- | --- |
| `relay` | `Relay` | The example: relays text both ways between the site and chosen channels. |
| `bank` | `Bank` | The guild bank ([bank.md](bank.md)): manager and requester DMs, snapshot posts, `/bank import`, `/bank find`, `/bank request` and the manager buttons. It also calls the hub's bank routes as the member who used it (`X-Toads-Acting-Member`). |

## Contract

| Route | Body | Answer |
| --- | --- | --- |
| `PUT /api/bots/{bot}` | `BotManifest {name, description, actions[], events[]}` | the manifest |
| `GET /api/bots` | | every registered manifest |
| `GET /api/bots/{bot}/actions?limit=` | | `SiteAction[] {id, bot, kind, payload, created_at, attempts}`, oldest first |
| `POST /api/bots/{bot}/actions/{id}/result` | `ActionResult {ok, refs, error}` | 204 |
| `POST /api/bots/{bot}/events` | `DiscordEvent {event_id, kind, occurred_at, guild_id, channel_id, user_id, payload}` | 202 `EventReceipt {accepted, duplicate, handled_by[]}` |

The rules:

- Bot names match `^[a-z][a-z0-9_-]{0,39}$` and kinds match `^[a-z][a-z0-9_.]{0,63}$`.
- Once a bot has registered, the site can send it only the action kinds its manifest lists (otherwise 422). Actions
  sent before a bot's first start wait for it.
- A failed result (`ok: false`) puts the action back in the queue until its fifth attempt, when it is given up.
  `on_result` listeners hear the final answer, which is how a feature keeps the message id its post became. A second
  answer to a finished action (the bot resending after a lost response) changes nothing.
- An event from a bot that has not registered gets 409, and an event kind the bot did not declare gets 422. Each
  `on_event` listener hears an `event_id` once: a resend reaches only the listeners that have not taken it, and one
  that fails makes the hub answer 503 so the bot resends. Use a stable id such as `message:<discord id>`.

What the bot does about the hub going away:

- Every action run registers the manifest again, so an API restart (which empties the in-memory registry) is
  healed within a run. An event answered with 409 registers and resends at once.
- An event the hub cannot take (network, 5xx) waits in the bot's `EventOutbox` and is resent in order on the next
  run. The outbox is bounded (1,000 events) and in memory, so a bot restart during an outage loses what it held. A
  4xx other than 409 is final and the event is dropped with a log line.
- A result the bot could not report is kept and sent again when the action comes back, so the action is never
  carried out twice.

## Making a new bot

1. Write a binding in `toads_bot/kit/` (or next to the feature it serves):

   ```python
   class Signups(Binding):
       site_actions: ClassVar[dict[str, str]] = {"open_signup": "open_signup"}
       discord_events: ClassVar[tuple[str, ...]] = ("signup",)

       async def open_signup(self, action: SiteAction) -> Refs:
           ...  # post the sign-up message in Discord
           return {"message_id": sent.id}

       @commands.Cog.listener()
       async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
           await self.emit(
               "signup",
               event_id=f"signup:{payload.message_id}:{payload.user_id}",
               user_id=payload.user_id,
               payload={"message_id": payload.message_id, "emoji": str(payload.emoji)},
           )
   ```

2. Add a spec to `SPECS` in `toads_bot/kit/specs.py`, for example
   `BotSpec(name="signups", description="…", bindings=(Signups,))`. Set `message_content=True` only if the bot
   reads message text, which is a privileged intent.
3. On the site, send and listen through `services.bots`:

   ```python
   services.bots.send("signups", "open_signup", {"channel_id": 111, "raid": "ssc-1001"})


   @services.bots.on_event("signups", "signup", name="raid-signups")
   def record(bot: str, event: DiscordEvent) -> None: ...
   ```

4. Run it with its own Discord application token, one process per bot:
   `TOADS_BOT_SPEC=signups TOADS_DISCORD_BOT_TOKEN=… TOADS_BOT_CHANNEL_IDS=[111] toads-botkit`.

## Not yet

- **Permissions.** The routes take the bots' service token only. Every binding runs with `OpenGate`, and the site's
  listeners get the Discord user id unverified. A role-backed `Gate` and per-listener checks come later
  (REQ-HUB-BOT-005). The bank bot is the exception for its own routes: it acts as the member through the hub, which
  reads that member's roles from Discord (see bank.md, "Acting for a member").
- **Storage.** `BotBridge` keeps its queue in memory (`InMemoryBridgeStore`), so an API restart drops unsent
  actions. A table behind `BridgeStore` replaces it without changing the rules.
- **The Toad Bot.** The existing Toad Bot (`toads_bot.cogs.community`, `/api/bot/*`) still runs on its own outbox.
  It can move onto the kit as a `Community` binding once the bridge has its table.
