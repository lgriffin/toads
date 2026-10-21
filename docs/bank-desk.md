# The bank request desk

Members ask the guild bank for an item from Discord with the Toad Bot, officers approve or deny each request with a
message on the Bank page, and the Toad Bot DMs the member the answer. Every request stays on the member's record.

It is the hub's own, in hub-db (`bank_item_requests`, migration `0029`), and needs neither ToadsBank nor a bank snapshot
([bank.md](bank.md)), so officers can work requests before the bank's stock is imported. ToadsBank's `/bank request`
(the bank bot) resolves an item against imported stock; the desk takes any item name as typed.

```
 member ──/bankrequest──▶ Toad Bot ──POST /api/bank-desk/requests (hub token, acting member)──▶ hub API
 officer ──Bank page──▶ POST /api/days/{day}/bank-desk/requests/{id}/approve|deny ──▶ hub API ──bot_outbox send_dm──▶
                                                                          Toad Bot ──DM──▶ member
```

## Asking

`/bankrequest item:<name> quantity:<1-1000>` in the Toads server. The Toad Bot calls the hub with the shared
`TOADS_HUB_SERVICE_TOKEN` and `X-Toads-Acting-Member: <discord user id>`; the hub reads the member's roles from Discord
(as for `/raidhelper import`), so only members of the server can ask, and the token can act for a member on this one
route (`TOAD_BOT_ACTING_PATHS` in `rbac/deps.py`) and never answer for an officer. The answer is ephemeral: the request's
number and that a DM will follow. Members can also ask on the Bank page.

An item is 1 to 100 characters (whitespace collapsed); quantity 1 to 1,000. Requests are kept by Discord user id, so a
member need not have signed in to the hub.

## Answering

| Route | Permission |
| --- | --- |
| `POST /api/bank-desk/requests` | `REQUEST_BANK_ITEMS` (every member) |
| `GET /api/bank-desk/requests/mine` | `VIEW_BANK`: the caller's own requests, newest first |
| `GET /api/days/{day}/bank-desk/requests?status=` | `MANAGE_BANK` (scoped): every request, newest first |
| `GET /api/days/{day}/bank-desk/members/{discord_user_id}/requests` | `MANAGE_BANK` (scoped): one member's history |
| `POST /api/days/{day}/bank-desk/requests/{id}/approve\|deny` | `MANAGE_BANK` (scoped), body `{"message": "..."}` |

`MANAGE_BANK` is held by every raid night's officers and the global tier, and by a member a super admin granted the
bank's upkeep ([bank.md](bank.md) "Grants"): that grant is how a banker will be set up. Requests do not belong to a raid
night yet, so every night's officers see the same desk under their own night's URL.

Answering a pending request records the status, the message (up to 500 characters), the officer and the time, queues a
`send_dm` job in `bot_outbox` and writes `bank_desk.approve` or `bank_desk.deny` to the audit log, all in one
transaction. A request already answered is refused with `409`, and no second DM is sent.

## The DM

The Toad Bot's outbox poll (`cogs/community.py`, every 30 seconds) sends the DM with no mentions allowed and acks the
job. If Discord refuses it (the member left, or turned off DMs from server members), the bot acks with the reason; the
desk shows each answer's DM as on its way, sent, or failed with that reason.

## On the site

`BankDesk.svelte` is on the Bank page for officers: they see the waiting requests (oldest first) or every request,
answer each with an optional message, and open any member's history.

Members ask once and read once (REQ-HUB-BDESK-008). The Bank page's **Ask the bank** form (`BankLive.svelte`) sends an
item the bank's stock list holds to ToadsBank, which sets it aside at once (it asks who it is for, and which bank when
more than one holds it), and anything else to this desk for an officer to answer. **Your requests** lists both, newest
first, in plain words: when they asked, what, the answer and the officer's message, and whether the Toad Bot's DM
reached them; stock requests still held can be cancelled there. The merge is `$lib/bank-mine.ts`. When the bank's stock
is not on the hub yet, or does not load, the form still asks the desk. Redeeming an officer token sits behind a "Have an
officer token?" disclosure at the foot of the page, since few members ever hold one. On the held page for officers, the
desk keeps its own ask form and list (`own`, true by default). While the launch
hold keeps the Bank page's Forever preview (`apps/web/src/lib/launch.ts`), the officers' held page still shows the desk
above the preview, so requests can be worked before launch. The static preview answers it from
`src/lib/preview/bank-desk-fake.ts`.
