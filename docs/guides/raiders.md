# Guide for raiders and trials

This guide is for everyone on a raid team: trials and raiders on Wednesday, Thursday or Sunday. If you are still
applying, start with the [visitors' guide](visitors.md).

## Logging in

Press **Log In with Discord** in the top bar of [toads.gg](https://toads.gg). The hub reads your raid night from your
Discord roles in the toads server, so there is no separate account or password. Log out from the menu under your name.

Once you are in, the top bar changes:

- **Hub** opens a menu of the pages every member uses (Hub Home, Raid, Logs, Highlights, Bank), and under
  "About the Guild" the public pages.
- **Me** is your own page.
- The menu under **your name** holds Account Settings, Your Setup, What You Can Do and Log Out.

### Trial or raider: what is the difference?

Trials can do everything on Me (performance, claims, specs, absences). Posting photos, streams and clips is for
raiders. The **What You Can Do** page marks anything that needs a raider role.

## Your first sign-in

The first time you log in, the hub opens **Your Setup** before anything else. It asks for what your officers need to
know about you:

1. **Your main.** Search for your main character. If the guild's logs do not know it yet (a new character, or one that
   has not raided with us), name it and pick its class instead; the hub picks it up once it appears in a log.
2. **Your specs.** Your class, a primary spec and, if you have one, a secondary spec. Officers build the raid comps
   from these.
3. **Your alts**, the same way as your main.
4. **Your professions**, with your skill and specialisation if you have one.

Everything is saved as you go. Press **Finish and hop in** to reach the hub, or **Finish later** to skip for now (until
you finish, logging in brings you back here first). You can run setup again any time from **Your Setup** in your
account menu.

If an officer imported your night's Raid-Helper sign-up, your class and spec may already be filled in. Me says so;
change them or press **Confirm my specs** to make them yours. Later imports never touch specs you set yourself.

After setup, the **Welcome** page (`/welcome`) is a short checklist of what else is worth doing once: choosing the name
the hub shows, reading How We Raid, meeting the bank and getting the analyzer's Windows app.

## Hub Home

Your home page. It shows officer posts, your next raid, how you did in your last raid, recent highlights, progression
and what we are recruiting. Press **Customise** to choose which cards you see and in what order; the choice is saved to
your account.

## Me

Me is your own page, and nobody else can open yours. It has four parts, with a jump list under the heading.

### Your raids

Your raids as the analyzer sees them, for one character at a time (the dropdown switches between your characters;
your main is marked "(main)"):

- one chart per role you played, with your headline number (healing, damage, or damage taken for a tank) against the
  **median of the same role** in each raid, never against everyone;
- your personal bests per role;
- raid by raid: your number, the role median, how far above or below it you were and your place in the role. Each raid
  links to its page under Logs;
- across your raids: the lowest, average and highest of each number, your most cast spells and your consumables,
  including how often you had a flask or elixir pair.

With fewer than three guild raids the charts say your history is building.

### Absences

Tell your officers which raid nights you will miss. Pick the night (if you are on two teams), the first date and
optionally the last date, and write a short note. The note is only seen by that night's officers. You can change or
delete an absence until it has passed. Please add them as early as you can: the officers see them on their calendar and
in the "Tonight" view before invites.

### Characters, specs and professions

- **Claim a character** (also at `/me/claim`): search for the character by name. A character whose name matches your
  Discord nickname is approved straight away; anything else waits for an officer of your raid night to approve it.
  Approved characters carry your performance and badges.
- **Your main** is the first character an officer approved for you. To change it, open the alt and press
  **Make <name> my main**. An officer of your night approves the swap; you can withdraw it while it waits, and if they
  turn it down the reason shows here.
- **Your specs** and **your professions**, as in setup. If an officer names you the guild's crafter for a profession,
  it says so here with their note on what to send you.

### Badges and toads

Your toads: the member toad everyone wears, your night's Toad badge, the class and Tank, Healer or Damage badges your
spec earns, and any awards the officers have given you (Raider of the Week, milestones, achievements and the rest).

## Account Settings

- **Your name on the hub:** show yourself by your Discord nickname or by one of your claimed characters.
- **Your Warcraft Logs key** (optional): with your own Warcraft Logs API client, analyses you ask for use your
  allowance instead of the guild's. Create a client at warcraftlogs.com/api/clients and paste its id and secret. The hub
  stores them encrypted and never shows them again.

## Raid

Your raid night's page. If you are on two teams, a switcher picks the night. It shows:

- **Strategy:** a button for each strategy doc your night's officers pinned ("Open the BWL strategy"). Docs live in
  Google Drive and open in a new tab. If one will not open, ask an officer to share it with you.
- **Your nights away:** your upcoming absences for this team.
- **Guild crafters** on your night, with their skill, specialisation and what to send them.

## Logs

Every raid the guild has logged, analysed. Pick a night's tab to see that night's widgets (last raid, recent raids,
attendance, boss kills, consumables, flasks and more), use the weekday chips, zone picker and search to narrow the list,
and open a raid to see its encounters, makeup by role, kill times and raid totals. **Boss history** sums kills and kill
times over the weekdays you picked.

On a raid's page, **You in this raid** shows your own number for the role you played against the raid's median and
your place. Other raiders' individual numbers are for officers only.

For a deeper look at any log on your own machine, download the analyzer's Windows app from the link on the Welcome page.

## Highlights

Raid night in pictures: photos, live streams and clips. You post them from Discord with the Toad Bot, and an officer of
your night approves each one before anyone else sees it.

| Command | What it does |
| --- | --- |
| `/highlight photo:<file> [caption]` | Posts a photo. Once approved it sits in the carousel for 48 hours, then in the archive for good. Up to 20 a day, 10 MB each. |
| `/stream start link:<twitch link> [title]` | Shows your Twitch stream under **Live now**. Your first stream from a channel waits for approval; after that, the channel is trusted and goes up at once. |
| `/stream end` | Takes your stream off the page. Streams also leave after 12 hours. |
| `/clip link:<url> title:<text>` | Shares a YouTube, Twitch clip or Streamable link for the officers to review. |

Photos are re-saved by the hub and their location data is stripped, so a phone photo never shares where you were. You
can take down your own photo or stream from the page. Everything here is for members only, unless the officers publish
a clip to the public Story.

## Bank

The guild bank, for flasks, potions and mats.

- **Inventory** lists what each bank holds. Press **Ask** beside an item, or fill in **Ask the bank**, to request it.
- In Discord, `/bankrequest item:<name> quantity:<n>` asks for anything by name. The Toad Bot DMs you the officers'
  answer.
- **Your requests** lists what you asked for and its status; cancel one you no longer need.
- If a super admin gives you an officer token to help run the bank, redeem it on the Bank page or with
  `/bank redeem <token>` in Discord.

## When something looks wrong

- **A page says you are not on a raid team:** your Discord roles do not put you on a night yet. Ask an officer.
- **Your performance is empty:** claim your character, and check the claim was approved. New raids appear after the
  hub's next refresh.
- **A strategy doc will not open:** it has not been shared with you in Google Drive. Ask your night's officers.
- **Anything else:** ask in Discord. Officers can see the same pages you can.
