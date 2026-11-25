# Guide for super admins

Super admins look after who can do what on the hub. You are also a global officer, so the
[officers' guide](officers.md) applies to you on every night. This guide covers the **Admin** console, which only super
admins see (Officers menu > Super Admin > Admin Console, or `/admin`).

Nothing on the hub can make someone a super admin. The list is set in the hub's configuration, so changing it is a job
for whoever runs the server ([ADMIN_GUIDE.md](../../ADMIN_GUIDE.md), "Access control").

## Officer grants

Officers normally come from Discord roles. To give someone officer powers without a role (cover for a night, a trusted
helper):

1. Under **Officer grants**, search the toads Discord by username or nickname.
2. Pick a raid night, or **Every night** to make them a global officer.
3. Grant. It counts on their next click; they do not need to log in again.

A grant only adds to what their Discord roles give, and revoking it leaves their roles' powers in place. It never makes
anyone a super admin, and a granted global officer cannot grant anything. It does not change Discord channels: if they
should sit interviews, put them on the night's interview panel too.

## Badges from Discord roles

Under **Badges from Discord roles**, pick a Discord role and a badge, then press **Give the badge to this role**.
Everyone holding the role wears the badge; **Remove** takes it off again.

Two kinds of badge do more than decorate:

- A night's **Toad badge** (Wednesday Toad, Thursday Toad, Sunday Toad) puts everyone holding the tied role on that
  night's team: its roster, its absences, its Raid page. When an officer accepts an applicant, the Toad Bot also gives
  them the role tied to the night's Toad badge.
- A night's **Officer badge** (Wednesday Officer and so on) makes everyone holding the tied role an officer of that
  night and no other.

Nothing is tied by default, so after a new night or a new Discord role, tie it here. Class, race, Tank, Healer and
Damage badges are cosmetic; members also earn their class and role badges from the spec they set on Me.

## Bank grants and officer tokens

To let a member who is not an officer help run the bank:

- **Grant** them snapshot imports, the request queue or both, for one night's banks or every bank, under
  "Super admins: who else runs the bank" on the Admin console.
- Or **mint an officer token** under **Officer tokens** in the same section: choose what it grants, the night, how
  long it lasts (7 days unless you change it, at most 30) and how many times it can be used. The token is shown
  **once**, so copy it and send it to the member in a DM. They redeem it on the Bank page or with
  `/bank redeem <token>`. You can revoke an unused token; grants already given from it stay until you revoke them in
  the grants list.

## View as

To check what a night's raiders or officers see, pick **Raider** or **Officer** and a night under **View as**, then
press "View as a Sunday raider" (or officer). Every page, menu and refusal is then the one that member would get.

- It is **read only**: nothing you do while viewing changes anything.
- A bar across the top says who you are viewing as, with **Back to super admin** (also in your account menu).
- You are still you: Me shows your own characters and absences through that role.

## Integrations and scheduled jobs

The Admin console also links each integration (Warcraft Logs, the Discord bots, the guild bank and Google Drive) and
lists what the hub refreshes on a schedule and how often. Setting up or fixing an integration is a server job; see
[ADMIN_GUIDE.md](../../ADMIN_GUIDE.md).

## Good to know

- Every grant, revoke, token, badge tie and View as is on the audit log with your name.
- When a member says a page is missing, check their Discord roles first, then their grants, then use View as for their
  night and role to see what they see.
