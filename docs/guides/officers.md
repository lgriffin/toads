# Guide for officers

This guide is for the officers of a raid night (Wednesday, Thursday or Sunday) and for global officers. You can do
everything in the [raiders' guide](raiders.md) too; this covers what being an officer adds.

## Your nights

Officer powers on the hub always belong to a raid night. You are an officer of a night because of your Discord role in
the toads server (or because a super admin granted it to you on the hub). A **global officer** is an officer of every
night and also holds a few guild-wide jobs, marked "global officers" below.

Everything a night owns is for that night's officers only: its officer section, task board, loot priority, absences,
character claims, applicants, interview panel and recruitment needs, its roster in the comp builder and professions,
its raids in full under Logs, its members' highlights waiting for approval, its strategy docs and its reference
comparisons. A Sunday officer sees and changes
Sunday's, never Wednesday's, and opening another night's page by its link shows a refusal instead of its content. If you
run two nights, you see both, each on its own. Global officers see every night, with a switcher.

## Finding your way around

Officers get an **Officers** menu in the top bar:

- **Officer Tools:** Officer Console, Character Claims, Calendar, Comp Builder, Professions, Recruitment and Strategy.
  Each one shows you only the nights you run.
- **Your Raid Night(s):** one entry per night you run, such as **Sunday Officers**, which opens that night's own
  section.

The officers' **desktop app** is the same hub in its own window, with these menus, a tray icon and desk alerts. Download
it from the latest `desktop-v…` release on [GitHub](https://github.com/lgriffin/toads/releases) and sign in with
Discord inside the app. [docs/desktop.md](../desktop.md) has the install steps for each computer.

## Your night's section

**Officers > Your Raid Night > <Night> Officers** (`/officers/nights/<night>`) is where a night is run. The **Raid**
page's "Running <night>" card links to it too.

- **Tonight:** for the ten minutes before invites. The next raid's date, who said they will miss it (with their spec
  and note), and how many tanks, healers and damage that leaves you short.
- **Strategy and roles:** your night's pinned links, such as the Google Drive strategy doc and role sheet. Pin a link
  with a name and its https address and every officer of your night sees it; **Unpin** takes it off. Up to 12.
- **Character claims** from your night's members (see below).
- **Every absence ahead** for your team.
- **Recruitment:** your night's interview panel and needs (see below).
- **Loot priority** (see below).
- **Task board:** To do, In progress and Done. Add a card with a title, notes, an assignee and a due date; drag it, or
  use Start it, Mark done and Back. Click a title to edit or remove it. Overdue cards are marked. You can assign a
  raider, but they cannot see the board, so tell them in Discord.

## Character claims and main swaps

**Officers > Character Claims** lists the claims waiting from your nights' members. A claim whose name matches the
member's Discord nickname is approved automatically; everything else waits for you. Approve the ones that are really
theirs and reject the rest.

Main swaps wait on the same panel: a member asks to make an approved alt their main, and you approve it or reject it
with a reason they will see on Me. Global officers also see a panel for members on no raid night.

## Absences and the Calendar

Members add the nights they will miss on Me, each with a note only you see. **Officers > Calendar** shows your nights'
upcoming absences a few weeks ahead. The same list is in your night's section, and the Tonight band shows the next
raid's.

## Recruitment

**Officers > Recruitment** has a card for each night you run.

- **Needs:** the specs your night wants, each with a priority. Search ("resto sha", "guardian") or pick from the list.
  **High** shows as "most wanted" on the homepage. Changes show on the homepage and the Recruit page straight away. An
  empty list says the night is full.
- **Interview panel:** who from the toads Discord interviews your night's applicants, up to 10 people. They do not need
  to have logged in to the hub. A change applies to the next application; rooms already open keep their people.
- **Decisions:** every application for your night still waiting, oldest first, with the answers, a link into the
  interview room and the applicant's logs. An application that names no night goes to the global officers only.
  - **Notes** are for officers only; the applicant never sees them.
  - **Accept** gives the applicant your night's raider role in Discord and posts a welcome in their room. Inviting them
    in game is still yours to do.
  - **Reject** declines the application and removes the interview room. They can apply again after 30 days.
  - The card also lists the last 14 days' decisions with what the Toad Bot reported. If it says it could not give a
    role, give it by hand in Discord and tell a super admin.

When someone applies for your night, the Toad Bot opens their `#interview-<character>` room with your panel in it. If
your night has no panel yet, the guild's default interviewers step in.

## Comp builder

**Officers > Comp Builder** plans a night's groups.

- **Any comp** seats bare specs, so you can try any composition. The panel beside the groups lists every raid buff,
  party buff and debuff, who brings it and, when nobody does, which class would.
- **Roster** switches to your night's members with the specs they set on Me. Filter by class, spec or role; the ⇄
  button swaps a seated member to their other spec. Members with no specs, including those who have never logged in,
  are listed under "without specs yet" so you can nudge them.
- Drag specs or members onto seats (on a phone, tap the member, then the seat). Raids seat 10, 20 or 40.
- **Lock in** saves the comp under a name for your night. Your night's officers can open, replace or delete it.

To fill in specs from your Raid-Helper sign-up, export the composition or event from Raid-Helper and run
`/raidhelper import night:<night> export:<file>` in Discord. The Toad Bot replies only to you with who was filled in and
who was skipped and why. Run it again whenever the sign-up changes; it never overwrites specs a member set themselves.

## Loot priority

In your night's section, **Loot priority** holds the big-ticket items your officers decide ahead of time.

1. Find an item by name and **Add** it. Each result links to Wowhead.
2. **Add to line** puts a member of your night's raid group in line; the arrows reorder, ✕ takes them out. Up to 10.
3. When someone gets the item, **Mark received**. The next person in line shows as **Next up**.
4. Write your reasoning in the item's note ("tanks before DPS"), and **Take off** an item once it is settled.

Raiders never see the list.

## Strategy docs

Strategy and role sheets stay in Google Drive; the hub only links them.

Each night keeps its own library: a doc belongs to the night that added it, and only that night's officers see, pin
or take it down. A doc a global officer adds is shared with every night, and only a global officer can take it down.

1. On **Officers > Strategy**, pick the raid (MC, BWL, ZG, AQ20, AQ40, Naxx or TBD), paste a
   `docs.google.com` or `drive.google.com` link, optionally name it, and press **Add the doc**.
2. Pin the docs your night's raiders need, on your night's Raid page or under "What each night's raiders see": tick one
   doc per raid the night runs, up to 10. Raiders see them on their Raid page in the order you ticked them.
3. Share each doc in Drive with the raiders. The hub cannot tell whether they can open it.

You can take down your night's own docs that no other night pins.

## Professions and guild crafters

**Officers > Professions** shows the professions of everyone on your night. Name a member the guild's crafter for a
profession they list, with a note on what to send them ("Flasks and transmutes"). Raiders see the guild's crafters on
their night's Raid page. The list of crafters is guild-wide, so every officer sees who to send recipes to.

## Logs in full

Members see the overview of every raid. As an officer you also see your night's raids **in full**: the Composition,
Healers, Tanks, Melee, Ranged, Consumables, Boss vs trash, Interrupts, Cast efficiency, Debuff and Totem uptime and
Engineering tabs, each raider's damage and healing per kill in Boss history, and the roster's badges. A raid on a
weekday none of your nights raids is in full for global officers only.

**Reference reports** (from the Officer Console, or `/officers/reference`) compare our raids with another guild's
report. A night sees only the references and comparisons its own officers imported or ran; older ones from before
nights were kept apart are shared, and only a global officer can relabel or delete them.

## Highlights approval

Photos and streams from your night's members wait for you in **Waiting for your approval** at the top of the
Highlights page. Approve puts a photo in the carousel for 48 hours, then the archive; turn down deletes it for good.
Approving a member's first stream from a channel trusts that channel, so their later streams go up at once.

Global officers also pick the **photo of the week**, review clips and decide whether a clip goes to members only or to
the public Story too, and can take down any photo or stream.

## The bank

On the **Bank** page officers also get:

- **Bank requests:** members' `/bankrequest` asks. Approve or deny each with a message, which the Toad Bot DMs to the
  member. You can open a member's request history.
- **Bank upkeep: requests and imports**, for your night's banks:
  - **Request queue:** approve, reject and record deliveries of requests made against the bank's stock.
  - **Import a bank export:** paste the export from the ToadsBank addon, check the preview, then accept it.

## Awards (global officers)

On the **Officer Console**, global officers give members their award toads: pick the member and the award. Raider of
the Month asks for the month and a weekly honour for the raid week. A note is optional and shows with the award. Awards
are guild-wide, so a night's officer cannot give them.

## Good to know

- Officer actions on the hub (approvals, decisions, loot, comps, board cards, strategy pins and more) are recorded in
  the hub's audit log with who did them and for which night.
- If a page refuses you, you are not an officer of that night. Ask a super admin if you should be.
- Need officer powers for a night you cover only now and then? A super admin can grant them on the hub without a
  Discord role.
