// Tiny static server for the e2e suite: serves ./build under BASE_PATH the way GitHub Pages does
// (directory index.html, 404.html fallback). Test-only; never used in production.
import { createReadStream, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize, resolve, sep } from 'node:path';

const root = resolve('build');
const base = process.env.BASE_PATH ?? '';
const port = Number(process.env.PORT ?? 4173);
const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain'
};

function file(path) {
  try {
    const s = statSync(path);
    if (s.isFile()) return path;
    if (s.isDirectory()) return file(join(path, 'index.html'));
  } catch {
    return null;
  }
  return null;
}

function send(res, status, path) {
  res.writeHead(status, { 'content-type': TYPES[extname(path)] ?? 'application/octet-stream' });
  createReadStream(path).pipe(res);
}

createServer((req, res) => {
  const url = new URL(req.url ?? '/', 'http://localhost');
  let pathname = decodeURIComponent(url.pathname);
  if (base && pathname === base) {
    res.writeHead(301, { location: `${base}/` }).end();
    return;
  }
  if (base && !pathname.startsWith(`${base}/`)) return send(res, 404, join(root, '404.html'));
  pathname = pathname.slice(base.length);
  const target = normalize(join(root, pathname));
  if (target !== root && !target.startsWith(root + sep)) return send(res, 404, join(root, '404.html'));
  const found = file(target);
  if (found && !pathname.endsWith('/') && found.endsWith(`${sep}index.html`) && !pathname.endsWith('index.html')) {
    res.writeHead(301, { location: `${base}${pathname}/` }).end();
    return;
  }
  if (found) return send(res, 200, found);
  send(res, 404, join(root, '404.html'));
}).listen(port, '127.0.0.1', () => console.log(`serving ${root} at http://127.0.0.1:${port}${base}/`));
