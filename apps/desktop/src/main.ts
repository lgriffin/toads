/**
 * Toads Hub desktop: the live hub in its own window (docs/desktop.md, REQ-HUB-APP-001..004).
 *
 * The window shows the website itself, so every page, permission and launch hold rule is the site's. What the app adds
 * is native: the Hub, Me and Officers menus with keyboard shortcuts, a remembered window, a tray icon, and for officers
 * a desk count on the dock or taskbar with a notification when new work arrives. Discord sign-in runs inside the
 * window and its session cookie is kept between launches. Pages from any other site open in the default browser.
 */
import {
  BrowserWindow,
  Menu,
  Notification,
  Tray,
  app,
  clipboard,
  dialog,
  nativeImage,
  nativeTheme,
  screen,
  session as sessions,
  shell,
  type MenuItemConstructorOptions,
  type Session,
  type WebContents
} from 'electron';
import { join } from 'node:path';

import { RECRUIT_DRAFT_KEY } from '../../web/src/lib/application';
import { DESKTOP_PATH, parseDesktopSite } from '../../web/src/lib/desktop';
import { SIGN_OUT } from '../../web/src/lib/nav';
import { badgeIcon, newWork, parseDesk, trayDesk, trayLines, waiting, type Desk } from './desk';
import { hubUrl, resolveHub } from './hub';
import { destination, permissionAllowed } from './links';
import { BUNDLED_SITE, menusFor, parseSession, type Link, type Menus } from './menus';
import { DEFAULT_PREFS, jsonFile, parsePrefs, type Prefs } from './prefs';
import { themeFromColor, windowBackground, type ThemeSource } from './theme';
import { plainChrome } from './useragent';
import { MIN_SIZE, parseState, restore } from './window-state';

const APP_ID = 'gg.toads.hub';
// One persistent partition: the hub's session cookie (and Discord's own sign-in) survive a restart.
const PARTITION = 'persist:toads';
const START_PATH = '/hub';
const DESK_POLL_MS = 2 * 60 * 1000;
const FOCUS_REFRESH_MS = 15 * 1000;
// A hub request that has not answered by then counts as no answer, so one stalled request never holds the menus.
const REQUEST_TIMEOUT_MS = 10 * 1000;
// A slow hub must not leave the app looking dead: the window shows by then even if the page has not painted yet.
const SHOW_BY_MS = 1000;
const GUIDE = 'https://github.com/lgriffin/toads/blob/main/docs/desktop.md#for-officers';
// ERR_ABORTED: a navigation the app itself cancelled (a link sent to the browser), not a failure to show offline for.
const ABORTED = -3;

const resources = (name: string) => join(app.getAppPath(), 'resources', name);
const staticFile = (name: string) => join(app.getAppPath(), 'static', name);

let hub = '';
let win: BrowserWindow | null = null;
let tray: Tray | null = null;
let quitting = false;
// The site's top bar lists and launch hold, from its /desktop.json; the bundled copy until it first answers.
let site = BUNDLED_SITE;
let menus: Menus = menusFor(null, site);
let desk: Desk | null = null;
let lastRefresh = 0;
let refreshing: Promise<void> | null = null;
// Bumped by Log out, so a refresh that started while still signed in never draws the signed-in menus afterwards.
let epoch = 0;
// Set by Log out: the next hub page forgets an unfinished application, as the site's Log out form does.
let forgetDraft = false;
const prefsFile = () => jsonFile(app.getPath('userData'), 'prefs.json');
let prefs: Prefs = DEFAULT_PREFS;

function hubSession(): Session {
  return sessions.fromPartition(PARTITION);
}

// ------------------------------------------------------------------------------------------------ links and safety

/** Send a link where it belongs: the hub and Discord sign-in into the window, http(s) to the browser, nothing else. */
function openLink(url: string): void {
  const where = destination(url, hub);
  if (where === 'app') void win?.loadURL(url);
  else if (where === 'browser') void shell.openExternal(url);
}

function guardContents(contents: WebContents): void {
  contents.on('will-attach-webview', (event) => event.preventDefault());
  contents.setWindowOpenHandler(({ url }) => {
    openLink(url);
    return { action: 'deny' };
  });
  contents.on('will-navigate', (event) => {
    if (destination(event.url, hub) === 'app') return;
    event.preventDefault();
    openLink(event.url);
  });
  contents.on('will-redirect', (event) => {
    if (!event.isMainFrame || destination(event.url, hub) === 'app') return;
    event.preventDefault();
    openLink(event.url);
  });
}

function secureSession(ses: Session): void {
  ses.setUserAgent(plainChrome(ses.getUserAgent()));
  ses.setPermissionRequestHandler((_contents, permission, callback, details) =>
    callback(permissionAllowed(permission, details.requestingUrl, hub))
  );
  ses.setPermissionCheckHandler((_contents, permission, requestingOrigin) =>
    permissionAllowed(permission, requestingOrigin, hub)
  );
}

// ------------------------------------------------------------------------------------------------ the window

function go(path: string): void {
  showWindow();
  void win?.loadURL(hubUrl(hub, path));
}

function showWindow(): void {
  if (!win) win = createWindow();
  if (win.isMinimized()) win.restore();
  win.show();
  win.focus();
}

function createWindow(): BrowserWindow {
  const stateFile = jsonFile(app.getPath('userData'), 'window-state.json');
  const { maximized, ...bounds } = restore(
    parseState(stateFile.read()),
    screen.getAllDisplays().map((d) => d.workArea)
  );
  const window = new BrowserWindow({
    ...bounds,
    minWidth: MIN_SIZE.width,
    minHeight: MIN_SIZE.height,
    show: false,
    title: 'Toads Hub',
    backgroundColor: windowBackground(prefs.theme, nativeTheme.shouldUseDarkColors),
    icon: resources('icon.png'),
    webPreferences: {
      partition: PARTITION,
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      webviewTag: false,
      spellcheck: true
    }
  });
  if (maximized) window.maximize();
  // The first paint, or SHOW_BY_MS, whichever comes first; never after the window was closed to the tray meanwhile.
  let shown = false;
  const firstShow = () => {
    if (!shown && !window.isDestroyed()) window.show();
    shown = true;
  };
  window.once('ready-to-show', firstShow);
  setTimeout(firstShow, SHOW_BY_MS);

  window.on('close', (event) => {
    stateFile.write({ ...window.getNormalBounds(), maximized: window.isMaximized() });
    if (prefs.keepInTray && !quitting) {
      shown = true;
      event.preventDefault();
      window.hide();
    }
  });
  window.on('closed', () => {
    win = null;
  });
  window.on('focus', () => {
    if (Date.now() - lastRefresh > FOCUS_REFRESH_MS) void refresh();
  });

  const contents = window.webContents;
  let offlineTries = 0;
  contents.on('did-fail-load', (_event, code, _description, url, isMainFrame) => {
    if (!isMainFrame || code === ABORTED || destination(url, hub) !== 'app') return;
    // The offline page waits longer on each try in a row; reaching the hub again starts the count over.
    void window.loadFile(staticFile('offline.html'), { query: { url, tries: String(offlineTries++) } });
  });
  contents.on('did-navigate', (_event, url) => {
    if (destination(url, hub) === 'app') offlineTries = 0;
  });
  // A full page load is where sign-in and sign-out land, so the menus follow who is signed in.
  contents.on('did-navigate', () => void refresh());
  // The reader's theme on the site (its theme-color tag) becomes the app's: on each hub page, and when they change it.
  contents.on('did-change-theme-color', (_event, color) => onHub(contents) && setTheme(themeFromColor(color)));
  contents.on('did-finish-load', () => {
    if (!onHub(contents)) return;
    const page = contents.getURL();
    if (forgetDraft) {
      forgetDraft = false;
      void contents.executeJavaScript(`sessionStorage.removeItem(${JSON.stringify(RECRUIT_DRAFT_KEY)})`).catch(() => undefined);
    }
    contents
      .executeJavaScript(`document.querySelector('meta[name="theme-color"]')?.content ?? null`)
      // Only while the same page is showing: a later page's own theme wins.
      .then((color: unknown) => contents.getURL() === page && setTheme(themeFromColor(typeof color === 'string' ? color : null)))
      .catch(() => undefined);
  });
  contents.on('context-menu', (_event, params) => {
    const items: MenuItemConstructorOptions[] = [];
    for (const word of params.dictionarySuggestions.slice(0, 4)) {
      items.push({ label: word, click: () => contents.replaceMisspelling(word) });
    }
    if (items.length) items.push({ type: 'separator' });
    if (params.linkURL) {
      items.push(
        { label: 'Open link in browser', click: () => void shell.openExternal(params.linkURL) },
        { label: 'Copy link address', click: () => clipboard.writeText(params.linkURL) },
        { type: 'separator' }
      );
    }
    if (params.isEditable) items.push({ role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' });
    else if (params.selectionText) items.push({ role: 'copy' });
    while (items.at(-1)?.type === 'separator') items.pop();
    // On the page itself, a browser's Back, Forward and Reload.
    if (!items.length) items.push(...navigationItems(true));
    Menu.buildFromTemplate(items).popup({ window });
  });

  void window.loadURL(hubUrl(hub, START_PATH));
  return window;
}

/** True while the window shows a hub page (not Discord's sign-in, not the offline page). */
function onHub(contents: WebContents): boolean {
  return contents.getURL().startsWith(`${hub}/`);
}

/** Take on the site's theme: Electron's theme source (title bar, menus, the offline page) and the window colour. */
function setTheme(theme: ThemeSource): void {
  if (nativeTheme.themeSource !== theme) nativeTheme.themeSource = theme;
  win?.setBackgroundColor(windowBackground(theme, nativeTheme.shouldUseDarkColors));
  if (prefs.theme === theme) return;
  prefs = { ...prefs, theme };
  prefsFile().write(prefs);
}

// ------------------------------------------------------------------------------------------------ session and desk

async function getJson(path: string): Promise<unknown> {
  try {
    const response = await hubSession().fetch(hubUrl(hub, path), {
      credentials: 'include',
      headers: { accept: 'application/json' },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
    });
    return response.ok ? await response.json() : null;
  } catch {
    return null; // offline, or the hub is down: the menus fall back to a visitor's
  }
}

/** Ask the hub who is signed in and, for officers, what waits on their desk; then redraw menus, tray and badge. */
function refresh(): Promise<void> {
  refreshing ??= (async () => {
    lastRefresh = Date.now();
    const started = epoch;
    const [answer, siteAnswer] = await Promise.all([getJson('/api/session'), getJson(DESKTOP_PATH)]);
    if (started !== epoch) return;
    // An older hub, or one that does not answer, keeps the last good lists (the bundled ones at first).
    site = parseDesktopSite(siteAnswer) ?? site;
    menus = menusFor(parseSession(answer), site);
    const officer = menus.tier === 'officer' || menus.tier === 'admin';
    const before = desk;
    desk = officer ? parseDesk(await getJson('/api/desk')) : null;
    if (started !== epoch) return;
    const news = newWork(before, desk);
    if (news && prefs.deskNotifications) notify(news);
    drawMenus();
    drawBadge();
  })().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

/** Log out as the site's account menu does (POST /auth/logout), then show the hub's front page signed out. */
async function signOut(): Promise<void> {
  try {
    await hubSession().fetch(hubUrl(hub, SIGN_OUT.href), {
      method: 'POST',
      credentials: 'include',
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
    });
  } catch {
    // Judged below by asking the hub who is signed in, not by the page the logout redirects to.
  }
  if (parseSession(await getJson('/api/session'))) {
    dialog.showErrorBox('Toads Hub', 'The hub did not answer, so you are still signed in. Try again.');
    return;
  }
  // Drop any refresh that began while signed in, and draw a visitor's menus at once.
  epoch += 1;
  refreshing = null;
  desk = null;
  forgetDraft = true;
  go('/');
  await refresh();
}

function notify(body: string): void {
  if (!Notification.isSupported()) return;
  const note = new Notification({ title: 'New on your desk', body, icon: resources('icon.png') });
  note.on('click', () => go(START_PATH));
  note.show();
}

function drawBadge(): void {
  const count = waiting(desk);
  app.setBadgeCount(count);
  const badge = badgeIcon(count);
  if (process.platform === 'win32' && win) {
    win.setOverlayIcon(badge ? nativeImage.createFromPath(resources(badge)) : null, badge ? `${count} waiting` : '');
  }
  tray?.setToolTip(['Toads Hub', ...trayLines(desk)].join('\n'));
}

// ------------------------------------------------------------------------------------------------ menus

function linkItems(groups: Link[][]): MenuItemConstructorOptions[] {
  return groups.flatMap((group, i) => [
    ...(i ? [{ type: 'separator' as const }] : []),
    ...group.map((link) => ({
      label: link.label,
      accelerator: link.accelerator,
      click: () => (link.signOut ? void signOut() : go(link.path))
    }))
  ]);
}

function setPref(key: keyof Prefs, value: boolean): void {
  prefs = { ...prefs, [key]: value };
  prefsFile().write(prefs);
  drawMenus();
}

function prefItems(): MenuItemConstructorOptions[] {
  return [
    {
      label: 'Keep running in the tray when closed',
      type: 'checkbox',
      checked: prefs.keepInTray,
      click: (item) => setPref('keepInTray', item.checked)
    },
    {
      label: 'Notify me about new desk work',
      type: 'checkbox',
      checked: prefs.deskNotifications,
      visible: menus.tier === 'officer' || menus.tier === 'admin',
      click: (item) => setPref('deskNotifications', item.checked)
    }
  ];
}

const mac = process.platform === 'darwin';

/** Back, Forward and Reload. `live` greys out a way that is closed, for a menu built at the moment it opens. */
function navigationItems(live = false): MenuItemConstructorOptions[] {
  // Looked up on each use: the app menu is built before the window exists and outlives a closed one.
  const history = () => win?.webContents.navigationHistory;
  return [
    {
      label: 'Back',
      accelerator: mac ? 'Cmd+[' : 'Alt+Left',
      enabled: !live || (history()?.canGoBack() ?? false),
      click: () => history()?.goBack()
    },
    {
      label: 'Forward',
      accelerator: mac ? 'Cmd+]' : 'Alt+Right',
      enabled: !live || (history()?.canGoForward() ?? false),
      click: () => history()?.goForward()
    },
    { role: 'reload' }
  ];
}

function drawMenus(): void {
  const page = () => win?.webContents.getURL() ?? '';
  const template: MenuItemConstructorOptions[] = [
    ...(mac ? [{ role: 'appMenu' as const }] : []),
    {
      label: 'File',
      submenu: [
        { label: 'Copy page address', accelerator: 'CmdOrCtrl+Shift+C', click: () => clipboard.writeText(page()) },
        {
          label: 'Open page in browser',
          accelerator: 'CmdOrCtrl+Shift+O',
          click: () => page().startsWith(hub) && void shell.openExternal(page())
        },
        { type: 'separator' },
        ...prefItems(),
        { type: 'separator' },
        { role: 'close' },
        ...(mac ? [] : [{ role: 'quit' as const }])
      ]
    },
    { role: 'editMenu' },
    {
      label: 'View',
      submenu: [
        ...navigationItems(),
        { role: 'forceReload' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
        { type: 'separator' },
        { role: 'toggleDevTools' }
      ]
    },
    ...menus.menus.map((m) => ({ label: m.label, submenu: linkItems(m.groups) })),
    { role: 'windowMenu' },
    {
      role: 'help',
      submenu: [
        { label: 'Desktop app guide', click: () => void shell.openExternal(GUIDE) },
        { label: 'Open Toads Hub in your browser', click: () => void shell.openExternal(hubUrl(hub, '/')) },
        ...(mac ? [] : [{ type: 'separator' as const }, { role: 'about' as const, label: 'About Toads Hub' }])
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
  drawTray();
}

function drawTray(): void {
  if (!tray) {
    tray = new Tray(nativeImage.createFromPath(resources('tray.png')));
    tray.setToolTip('Toads Hub');
    tray.on('click', showWindow);
  }
  // The desk under its heading; each line opens the desk on the hub home.
  const [heading, ...lines] = trayDesk(desk);
  const template: MenuItemConstructorOptions[] = [
    { label: 'Open Toads Hub', click: showWindow },
    ...(heading
      ? [
          { type: 'separator' as const },
          { label: heading, enabled: false },
          ...lines.map((label) => ({ label, click: () => go(START_PATH) }))
        ]
      : []),
    ...(menus.officerQuickLinks.length
      ? [{ type: 'separator' as const }, ...linkItems([menus.officerQuickLinks])]
      : []),
    { type: 'separator' },
    ...prefItems(),
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        quitting = true;
        app.quit();
      }
    }
  ];
  tray.setContextMenu(Menu.buildFromTemplate(template));
}

// ------------------------------------------------------------------------------------------------ start

function start(): void {
  try {
    hub = resolveHub(process.argv, process.env);
  } catch (error) {
    dialog.showErrorBox('Toads Hub', error instanceof Error ? error.message : String(error));
    app.exit(1);
    return;
  }
  if (!app.requestSingleInstanceLock()) {
    app.quit();
    return;
  }
  if (process.platform === 'win32') app.setAppUserModelId(APP_ID);
  app.userAgentFallback = plainChrome(app.userAgentFallback);
  app.setAboutPanelOptions({
    applicationName: 'Toads Hub',
    applicationVersion: app.getVersion(),
    copyright: 'The Toads of Spineshatter',
    website: hub,
    iconPath: resources('icon.png')
  });

  app.on('web-contents-created', (_event, contents) => guardContents(contents));
  app.on('second-instance', showWindow);
  app.on('activate', showWindow);
  app.on('before-quit', () => {
    quitting = true;
  });
  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
  });

  void app.whenReady().then(() => {
    prefs = parsePrefs(prefsFile().read());
    nativeTheme.themeSource = prefs.theme;
    // A reader who follows their device: keep the window colour with it when it turns from day to night.
    nativeTheme.on('updated', () => win?.setBackgroundColor(windowBackground(prefs.theme, nativeTheme.shouldUseDarkColors)));
    secureSession(hubSession());
    drawMenus();
    win = createWindow();
    setInterval(() => void refresh(), DESK_POLL_MS);
  });
}

start();
