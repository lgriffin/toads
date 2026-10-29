// Starts the built app (dist/main.cjs) against a fake hub and checks what a unit test cannot: the window opens the hub,
// links to other sites go to the browser, sign-in's cookie reaches the main process's requests, the menus become an
// officer's from the live site's /desktop.json, new desk work raises a notification, the window takes the site's theme,
// Log out signs the member out, and the offline page retries by itself. Run with `npm run smoke` (on Linux CI under
// xvfb-run).
const assert = require('node:assert/strict');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const { app, Menu, Notification, nativeTheme, shell } = require('electron');
const { start } = require('./fake-hub.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const opened = [];
const notes = [];
let menu = [];

app.setAppPath(ROOT);
app.setPath('userData', fs.mkdtempSync(path.join(os.tmpdir(), 'toads-hub-smoke-')));
shell.openExternal = async (url) => void opened.push(url);
const setMenu = Menu.setApplicationMenu.bind(Menu);
Menu.setApplicationMenu = (m) => {
  menu = m ? m.items.map((i) => ({ label: i.label, items: (i.submenu?.items ?? []).map((s) => s.label) })) : [];
  return setMenu(m);
};
// CI has no notification server; the app's own check would skip the alert.
Notification.isSupported = () => true;
Notification.prototype.show = function () {
  notes.push(this.body);
};

const until = async (what, check, ms = 15000) => {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (await check()) return;
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error(`timed out waiting for ${what}`);
};
const labels = () => menu.map((m) => m.label);
const submenu = (label) => menu.find((m) => m.label === label)?.items ?? [];

async function run() {
  const hub = await start();
  const origin = `http://127.0.0.1:${hub.address().port}`;
  process.argv.push(`--hub=${origin}`);
  require(path.join(ROOT, 'dist', 'main.cjs'));
  await app.whenReady();

  await until('the window', () => app.isReady() && require('electron').BrowserWindow.getAllWindows().length === 1);
  const win = require('electron').BrowserWindow.getAllWindows()[0];
  const contents = win.webContents;
  await until('the hub page', () => contents.getURL() === `${origin}/hub` && !contents.isLoading());
  await until('the visitor menus', () => submenu('Me').includes('Log in with Discord'));
  await until("the site's theme", () => nativeTheme.themeSource === 'dark');
  assert.ok(!labels().includes('Officers'), 'a visitor has no Officers menu');

  const click = (id) => contents.executeJavaScript(`document.getElementById('${id}').click()`);
  for (const id of ['docs', 'tab', 'channel']) await click(id);
  await click('file');
  await until('links in the browser', () => opened.length === 3);
  assert.deepEqual(opened, [
    'https://docs.google.com/document/d/strategy',
    'https://www.warcraftlogs.com/reports/abc',
    'https://discord.com/channels/1/2'
  ]);
  assert.equal(contents.getURL(), `${origin}/hub`, 'the window stays on the hub');
  assert.equal(require('electron').BrowserWindow.getAllWindows().length, 1, 'no second window opens');

  await click('login');
  await until('the officer menus', () => labels().includes('Officers'));
  assert.ok(submenu('Officers').includes('Officer console'));
  assert.ok(submenu('Officers').includes('Wednesday officers'));
  assert.ok(!submenu('Officers').includes('Sunday officers'), 'only the nights this officer runs');
  assert.ok(!submenu('Officers').includes('Admin console'));
  assert.ok(submenu('Me').includes('Me'));
  assert.ok(submenu('Hub').includes('Raid toolkit'), "the live site's lists win over the bundled ones");
  assert.ok(submenu('Me').includes('Log out'));

  // A reader who picked the light theme on the site: the app's theme follows, and is remembered for the next launch.
  await contents.loadURL(`${origin}/light`);
  await until('the light theme', () => nativeTheme.themeSource === 'light');
  await until('the remembered theme', () => {
    const prefs = path.join(app.getPath('userData'), 'prefs.json');
    return fs.existsSync(prefs) && JSON.parse(fs.readFileSync(prefs, 'utf-8')).theme === 'light';
  });
  await contents.loadURL(`${origin}/hub`);

  // Another full page load looks at the desk again; the fake desk has one more application each time.
  contents.reload();
  await until('a desk notification', () => notes.length === 1);
  assert.match(notes[0], /Applications waiting: \d+ \(1 new\)/);

  // Log out from the Me menu posts to the hub as the site does; the menus go back to a visitor's.
  Menu.getApplicationMenu().items.find((i) => i.label === 'Me').submenu.items.find((i) => i.label === 'Log out').click();
  await until('signed out', () => submenu('Me').includes('Log in with Discord'));
  assert.ok(!labels().includes('Officers'));
  assert.equal(contents.getURL(), `${origin}/`, "Log out lands on the hub's front page");

  // With the hub gone, the window shows the offline page, whose Try again link goes back to the page that failed.
  hub.close();
  hub.closeAllConnections();
  contents.reload();
  await until('the offline page', () => contents.getURL().startsWith('file:') && !contents.isLoading());
  assert.equal(
    await contents.executeJavaScript("document.getElementById('retry').href"),
    `${origin}/`
  );
  // It wears the site's mark (copied in by the build, allowed by its CSP) and counts down to trying by itself.
  await until('the mark', () => contents.executeJavaScript("document.querySelector('.brand img').naturalWidth > 0"));
  assert.match(await contents.executeJavaScript("document.getElementById('wait').textContent"), /^Trying again in \d+ s$/);

  console.log('desktop smoke: ok');
  app.exit(0);
}

run().catch((error) => {
  console.error(error);
  app.exit(1);
});
