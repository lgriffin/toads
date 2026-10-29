// A stand-in for the hub on localhost: a page with links, a sign-in that sets the session cookie, /api/session and a
// desk whose applications grow by one on each look. Used only by smoke.cjs.
const http = require('node:http');

const SESSION = {
  member_id: 7,
  display_name: 'Hopscotch',
  global_officer: false,
  super_admin: false,
  day_roles: { wednesday: 'officer' },
  raid_days: ['wednesday'],
  officer_days: ['wednesday'],
  day_names: { wednesday: 'Wednesday', sunday: 'Sunday' }
};

// The site's /desktop.json (apps/web/src/lib/desktop.ts), with a Hub page the bundled lists lack, so the smoke run
// sees the live lists win over the bundled ones.
const item = (href, label) => ({ href, label });
const SITE = {
  contract: 1,
  launch_hold: false,
  nav: {
    publicNav: [item('/', 'Home'), item('/recruit', 'Recruit')],
    memberNav: [item('/hub', 'Hub'), item('/toolkit', 'Raid toolkit'), item('/me', 'Me'), { ...item('/officers', 'Officers'), officerOnly: true }],
    hubMenu: [item('/hub', 'Hub home'), item('/toolkit', 'Raid toolkit')],
    officerMenu: [item('/officers', 'Officer console')],
    accountMenu: [item('/me/settings', 'Account settings'), item('/setup', 'Your setup'), item('/features', 'What you can do')]
  }
};

function start() {
  let applications = 0;
  const server = http.createServer((req, res) => {
    const signedIn = (req.headers.cookie || '').includes('toads_session=yes');
    const json = (code, body) => {
      res.writeHead(code, { 'content-type': 'application/json' });
      res.end(JSON.stringify(body));
    };
    if (req.url === '/api/session') return signedIn ? json(200, SESSION) : json(401, { detail: 'not signed in' });
    if (req.url === '/api/desk') {
      applications += 1;
      return json(200, { applications_waiting: applications, posts_to_curate: 0, highlights_to_review: 0, spotlights_awaiting_consent: 0 });
    }
    if (req.url === '/desktop.json') return json(200, SITE);
    if (req.url === '/auth/logout' && req.method === 'POST') {
      res.writeHead(303, { location: '/', 'set-cookie': 'toads_session=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax' });
      return res.end();
    }
    if (req.url === '/auth/login') {
      res.writeHead(302, { location: '/hub', 'set-cookie': 'toads_session=yes; Path=/; HttpOnly; Secure; SameSite=Lax' });
      return res.end();
    }
    // The site's theme-color tag: /light is a reader who picked the light theme.
    const color = req.url === '/light' ? '<meta name="theme-color" content="#f6f1e5">' : '<meta name="theme-color" content="#120f33">';
    res.writeHead(200, { 'content-type': 'text/html' });
    res.end(`<!doctype html><title>Hub</title>${color}<h1>Hub</h1>
      <a id="docs" href="https://docs.google.com/document/d/strategy">Strategy doc</a>
      <a id="tab" href="https://www.warcraftlogs.com/reports/abc" target="_blank">Logs</a>
      <a id="channel" href="https://discord.com/channels/1/2">Discord channel</a>
      <a id="file" href="file:///etc/passwd">A file</a>
      <a id="login" href="/auth/login">Log in</a>`);
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server)));
}

module.exports = { start };
