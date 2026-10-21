export interface NavItem {
  href: string;
  label: string;
  /** Shown only to officers; the API is still the gate. */
  officerOnly?: boolean;
  /** Shown only to super admins; the API is still the gate. */
  adminOnly?: boolean;
  /** One plain sentence under the link in a top bar menu, so a reader knows what is behind it before they open it. */
  hint?: string;
}

/** A labelled group of links inside one top bar menu. */
export interface NavGroup {
  label: string;
  items: NavItem[];
}

/** The public face: the landing page, how we raid, the hub's features, the outward story and recruitment. No login. */
export const PUBLIC_NAV: readonly NavItem[] = [
  { href: '/', label: 'Home' },
  { href: '/how-we-raid', label: 'How we raid' },
  { href: '/features', label: 'Hub features' },
  { href: '/story', label: 'Story' },
  { href: '/recruit', label: 'Recruit' }
];

/** The inward hub, shown once a member signs in. */
export const MEMBER_NAV: readonly NavItem[] = [
  { href: '/hub', label: 'Hub' },
  { href: '/raid', label: 'Raid' },
  { href: '/logs', label: 'Logs' },
  { href: '/highlights', label: 'Highlights' },
  { href: '/bank', label: 'Bank' },
  { href: '/me', label: 'Me' },
  { href: '/officers', label: 'Officers', officerOnly: true },
  { href: '/admin', label: 'Admin', adminOnly: true }
];

/** Member pages outside the nav: the first sign-in checklist. */
export const MEMBER_EXTRA: readonly string[] = ['/welcome'];

export function memberNav(officer: boolean, admin = false): NavItem[] {
  return MEMBER_NAV.filter((i) => (officer || admin || !i.officerOnly) && (admin || !i.adminOnly));
}

// The top bar for a signed-in member: Hub (a menu of the pages every member uses), Me, and for officers and super
// admins one Officers menu. Visitors keep the public nav. Every route still checks its own permission.

/** The pages under the Hub menu, with what each holds. */
export const HUB_MENU: readonly NavItem[] = [
  { href: '/hub', label: 'Hub home', hint: 'Posts, your next raid and how you did' },
  { href: '/raid', label: 'Raid', hint: 'Your raid night: role, sign-ups and prep' },
  { href: '/logs', label: 'Logs', hint: 'Every raid we logged, fight by fight' },
  { href: '/highlights', label: 'Highlights', hint: 'Clips and spotlights from raid night' },
  { href: '/bank', label: 'Bank', hint: 'Ask the guild bank for flasks and mats' }
];

/** The officers' shared tools, under the Officers menu. Each page still shows an officer only their own nights. */
export const OFFICER_MENU: readonly NavItem[] = [
  { href: '/officers', label: 'Officer console', hint: 'Claims, applications and awards' },
  { href: '/officers/claims', label: 'Character claims', hint: 'Approve the characters members claim' },
  { href: '/officers/calendar', label: 'Calendar', hint: 'Who will miss your raid nights' },
  { href: '/officers/comp', label: 'Comp builder', hint: 'Plan groups and buffs' },
  { href: '/officers/professions', label: 'Professions', hint: 'Who crafts what, and the guild’s crafters' },
  { href: '/officers/recruitment', label: 'Recruitment', hint: 'Interview panels for each night' }
];

/** The Hub menu: the member pages this member may open, then the public pages under "About the guild". */
export function hubMenu(members: readonly NavItem[]): NavGroup[] {
  const open = new Set(members.map((i) => i.href));
  return [
    { label: 'Your hub', items: HUB_MENU.filter((i) => open.has(i.href)) },
    { label: 'About the guild', items: [...PUBLIC_NAV] }
  ];
}

/**
 * The Officers menu: the shared tools, then only the raid nights this officer runs (a Sunday officer never sees a
 * Wednesday entry), then the Admin console for super admins. Empty for a member with neither power.
 */
export function officerMenu(
  officer: boolean,
  admin: boolean,
  nights: readonly { day: string; name: string }[] = []
): NavGroup[] {
  const groups: NavGroup[] = [];
  if (officer || admin) {
    groups.push({ label: 'Officer tools', items: [...OFFICER_MENU] });
    if (nights.length) {
      groups.push({
        label: nights.length === 1 ? 'Your raid night' : 'Your raid nights',
        items: nights.map((n) => ({ href: `/officers/nights/${n.day}`, label: `${n.name} officers`, hint: 'Claims, absences, tasks and interviews' }))
      });
    }
  }
  if (admin) {
    groups.push({ label: 'Super admin', items: [{ href: '/admin', label: 'Admin console', hint: 'Grants, badges and integrations', adminOnly: true }] });
  }
  return groups;
}

/** True when the page is one of the menu's links, so its button can show where the reader is. */
export function inMenu(pathname: string, groups: readonly NavGroup[]): boolean {
  return groups.some((g) => g.items.some((i) => isActive(pathname, i.href)));
}

/** The one link in a menu that marks the current page: the longest match, so Calendar wins over Officer console. */
export function currentIn(pathname: string, groups: readonly NavGroup[]): string | undefined {
  const hrefs = groups.flatMap((g) => g.items.map((i) => i.href)).filter((h) => isActive(pathname, h));
  return hrefs.sort((a, b) => b.length - a.length)[0];
}

export function isActive(pathname: string, href: string): boolean {
  const path = pathname.length > 1 && pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
  return href === '/' ? path === '/' : path === href || path.startsWith(`${href}/`);
}
