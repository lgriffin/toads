# Setting up Discord for Toads applications

When someone applies to Toads on the website, the **Toad Bot** creates a private channel on the Toads Discord server
called `#interview-<their character>`. Only the applicant and the interviewers for the night they picked (Wednesday,
Thursday or Sunday) can see it, and the applicant's answers are posted inside. Each night's officers choose those
interviewers on the website (Officers > Recruitment); until they do, `_gallagher` and `hadur117` interview everyone.

This guide is for the server admin. Everything is done by clicking in Discord. There is no coding and there are no
files, and no passwords to handle. It takes about 15 minutes.

## What is the Toad Bot, and how do I get it?

The Toad Bot is an automatic Discord account that the website controls. You never log in to it, install it or
download anything. You **add it to the server once** by opening a link, much like inviting a person. After that it
appears in the member list, and the website tells it what to do.

This is the link:

<https://discord.com/oauth2/authorize?client_id=1561652680768626688&permissions=268520464&integration_type=0&scope=bot+applications.commands>

> **Never paste a bot token into Discord, a chat or an e-mail.** The token is the bot's password. You never need it,
> and if anyone asks you for it, the answer is no.

Every step below ends with a **Check** line. If what you see doesn't match it, stop and look at
[If something looks wrong](#if-something-looks-wrong) before you carry on.

## Step 1: Add the Toad Bot to the server

1. Open [this link](https://discord.com/oauth2/authorize?client_id=1561652680768626688&permissions=268520464&integration_type=0&scope=bot+applications.commands) in a web browser where you are logged in to Discord.
2. Under **Add to server**, pick **Toads**.
3. Press **Continue**. Discord shows a list of permissions with ticks. **Leave every tick on**, because the bot needs
   them all. Press **Authorize**.
4. Complete the "I am human" check if Discord asks.

**Check:** the Toad Bot appears in the server's member list on the right, marked **APP**. It may show as offline
until Hadur starts it, and that's fine.

## Step 2: Turn on Developer Mode

Developer Mode adds a "Copy ID" option to Discord's right-click menus. It changes nothing else.

1. Click the **cog** (User Settings) next to your name, at the bottom left.
2. In the left-hand list, scroll down to **Advanced** under App Settings.
3. Switch **Developer Mode** on.
4. Press **Esc** to close the settings.

**Check:** when you right-click any channel, the bottom of the menu now says **Copy Channel ID**.

## Step 3: Make the interview category

Interview channels are created inside this category.

1. Right-click the server name **Toads** at the top left, then click **Create Category**.
2. Name it `Interviews`.
3. Switch **Private Category** on, then press **Next**.
4. On the "Add members or roles" screen, search for **Toad Bot**, tick it, and press **Create Category**. Don't add
   anyone else: the interviewers and each applicant are let into their own channel automatically.

**Check:** the `Interviews` category appears in the channel list with a padlock icon.

> If you skipped step 4, you can fix it: right-click `Interviews`, then **Edit Category**, **Permissions**, **Add
> members or roles**, **Toad Bot**. Then tick **View Channels**, **Manage Channels** and **Manage Permissions** for
> it, and press **Save Changes**.

## Step 4: Copy three numbers and send them to Hadur

Copy each number below and paste it into a direct message to Hadur, saying which is which. These are not secret.

1. **The category:** right-click `Interviews`, then **Copy Category ID**.
2. **_gallagher:** find them in the member list, right-click their name, then **Copy User ID**.
3. **hadur117:** the same as above.

They are long numbers, such as `1187654321098765432`. If what you pasted is a name or a link instead, copy it again.

**Check:** your message has three long numbers, each labelled.

## Step 5: Test it (after Hadur says it's live)

1. Ask someone who is **not** `_gallagher` or `hadur117` to apply on the website's **Recruit** page. They need to be
   in the Toads Discord first.
2. Within a minute, a channel called `#interview-<their character name>` appears under `Interviews`.

**Check:** the channel has a message from the Toad Bot that mentions the applicant, `_gallagher` and `hadur117`, with
the answers underneath. When you look at the channel's member list, it shows only those three, plus server admins.
(If the night the tester picked already has an interview panel on the website, the room has that panel instead.)

You're done. Server admins can always see every channel, so you will see interview channels too.

## If something looks wrong

| What you see | What to do |
| --- | --- |
| The link says "Unknown application" or "Invalid client" | The link was copied incompletely. Use the link at the top of this guide, or ask Hadur. |
| Toads isn't in the **Add to server** list | You don't have permission to manage the server. Ask the server owner to give you the **Manage Server** permission, or to do Step 1 themselves. |
| No **Copy ... ID** option on the right-click menu | Developer Mode is off. Do Step 2 again. |
| No channel appears after someone applies | Tell Hadur. Check first that the Toad Bot is shown as online in the member list. |
| The channel appears but someone else can see it | Right-click `Interviews`, then **Edit Category**, then **Permissions**. Make sure `@everyone` has **View Channels** switched off (a red ✕). |
| Applicants see "You are not in the Toads Discord" | They need to join the server with https://discord.gg/toads first, then press send again. |

## Keeping things working

The bot keeps working on its own permissions, so Hadur no longer needs to be a server admin once the test works. Keep
**Manage Server** and **Manage Roles** yourself, so you can fix the bot's access later. Don't remove the Toad Bot or
its role, and don't take its access to `Interviews` away.

---

The website side of this setup (creating the bot, building the link and the config) is in
[ADMIN_GUIDE.md](../ADMIN_GUIDE.md#getting-the-toad-bot-onto-the-server). You don't need it.
