// The static preview prerenders every page; the real deployment renders on the Node server.
export const prerender = __PREVIEW__;
export const trailingSlash = __PREVIEW__ ? 'always' : 'never';
