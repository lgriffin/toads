# Setting up Discord for Toads applications

This guide sets up the Discord side of the application page. When someone applies on the Toads website, the Toad Bot
makes a private channel on the Toads server called `#interview-<their character>`. Only the applicant, `_gallagher`
and `hadur117` can see it, and the applicant's answers are posted inside.

There are two parts, done by two different people:

- **Part 1, the server admin.** Everything is done by clicking in Discord. No coding, no files and no passwords to
  handle. It takes about 15 minutes.
- **Part 2, whoever runs the website.** This is the technical side. It is done before Part 1 starts and again after
  it finishes.

> **Never paste a bot token into Discord, a chat or an e-mail.** The token is the bot's password. The server admin
> never needs it, and if anyone asks the admin for it, the answer is no.

---

## Before you start (website person)

Do steps 1 to 3 of [Part 2](#part-2-the-website-side) first. That gives the server admin one link, **the invite
link**, to send in step A. Send the admin this guide and the link together.

---

## Part 1: the server admin

You need to be able to change the server's settings. If you own the server, you can.

Every step ends with a **Check** line. If what you see doesn't match it, stop and look at
[If something looks wrong](#if-something-looks-wrong) before you carry on.

### Step A: Add the Toad Bot to the server

1. Open the invite link you were sent, in a web browser where you are logged in to Discord.
2. Under **Add to server**, pick **Toads**.
3. Press **Continue**. Discord shows a list of permissions with ticks. **Leave every tick on**, because the bot needs
   them all. Press **Authorize**.
4. Complete the "I am human" check if Discord asks.

**Check:** the Toad Bot appears in the server's member list on the right, marked **APP**. It may show as offline
until the website person starts it, and that's fine.

### Step B: Turn on Developer Mode

Developer Mode adds a "Copy ID" option to Discord's right-click menus. It changes nothing else.

1. Click the **cog** (User Settings) next to your name, at the bottom left.
2. In the left-hand list, scroll down to **Advanced** under App Settings.
3. Switch **Developer Mode** on.
4. Press **Esc** to close the settings.

**Check:** when you right-click any channel, the bottom of the menu now says **Copy Channel ID**.

### Step C: Make the interview category

Interview channels are created inside this category.

1. Right-click the server name **Toads** at the top left, then click **Create Category**.
2. Name it `Interviews`.
3. Switch **Private Category** on, then press **Next**.
4. On the "Add members or roles" screen, search for **Toad Bot**, tick it, and press **Create Category**. Don't add
   anyone else: `_gallagher`, `hadur117` and each applicant are let into their own channel automatically.

**Check:** the `Interviews` category appears in the channel list with a padlock icon.

> If you skipped step 4, you can fix it: right-click `Interviews`, then **Edit Category**, **Permissions**, **Add
> members or roles**, **Toad Bot**. Then tick **View Channels**, **Manage Channels** and **Manage Permissions** for
> it, and press **Save Changes**.

### Step D: Copy three numbers and send them to the website person

Copy each number below and paste it into a direct message to the website person, saying which is which. These are
not secret.

1. **The category:** right-click `Interviews`, then **Copy Category ID**.
2. **_gallagher:** find them in the member list, right-click their name, then **Copy User ID**.
3. **hadur117:** the same as above.

They are long numbers, such as `1187654321098765432`. If what you pasted is a name or a link instead, copy it again.

**Check:** your message has three long numbers, each labelled.

### Step E: Test it (after the website person says it's live)

1. Ask someone who is **not** `_gallagher` or `hadur117` to apply on the website's **Recruit** page. They need to be
   in the Toads Discord first.
2. Within a minute, a channel called `#interview-<their character name>` appears under `Interviews`.

**Check:** the channel has a message from the Toad Bot that mentions the applicant, `_gallagher` and `hadur117`, with
the answers underneath. When you look at the channel's member list, it shows only those three, plus server admins.

You're done. Server admins can always see every channel, so you will see interview channels too.

### If something looks wrong

| What you see | What to do |
| --- | --- |
| The invite link says "Unknown application" or "Invalid client" | The link was copied incompletely. Ask the website person for it again. |
| Toads isn't in the **Add to server** list | You don't have permission to manage the server. Ask the server owner to give you the **Manage Server** permission, or to do Step A themselves. |
| No **Copy ... ID** option on the right-click menu | Developer Mode is off. Do Step B again. |
| No channel appears after someone applies | Tell the website person. Check first that the Toad Bot is shown as online in the member list. |
| The channel appears but someone else can see it | Right-click `Interviews`, then **Edit Category**, then **Permissions**. Make sure `@everyone` has **View Channels** switched off (a red ✕). |
| Applicants see "You are not in the Toads Discord" | They need to join the server with https://discord.gg/toads first, then press send again. |

### Stepping back afterwards

Once the test works, the website person no longer needs server admin. The bot keeps working on its own permissions.
Whoever stays as server admin should keep **Manage Server** and **Manage Roles**, so they can repair the bot's access
later.

---

## Part 2: the website side

This part is for whoever runs the hub. The technical background is in [ADMIN_GUIDE.md](../ADMIN_GUIDE.md), section 2,
"Discord permissions for interview rooms".

1. **Create or reuse the hub's Discord application.** Go to <https://discord.com/developers/applications>. Use the
   application the hub already signs in with; its bot is the Toad Bot. Under **Bot**, switch on **Server Members
   Intent** and **Message Content Intent**. The bot token goes only into `TOADS_DISCORD_BOT_TOKEN` in the API's and
   the bot's env on the server.
2. **Set the bot's name and picture.** Under **General Information**, name the application `Toad Bot` and give it the
   toad avatar. This is the name the server admin will see.
3. **Build the invite link.** Use the Application ID from **General Information**:

   ```text
   https://discord.com/oauth2/authorize?client_id=<APPLICATION ID>&scope=bot+applications.commands&permissions=268520464
   ```

   Open it once yourself and check that the permission list shows View Channels, Send Messages, Embed Links, Read
   Message History, Manage Channels and Manage Roles. Then send it to the server admin with this guide.
4. **When the admin sends the three numbers**, put them in `config/community.yaml` on the server. User ids are used,
   not usernames, so a renamed account can't take their place:

   ```yaml
   interview_category_id: 1187654321098765432
   interviewers:
     - "123456789012345678"   # _gallagher
     - "234567890123456789"   # hadur117
   ```

5. **Restart the API and the Toad Bot**, then confirm the bot shows as online in the server. Tell the admin to do
   Step E.

If the test fails, the bot's log names the cause: it reports interviewers it couldn't find, and Discord's "Missing
Permissions" errors when the category's permissions are wrong.
