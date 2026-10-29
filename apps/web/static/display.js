// Applies the reader's saved display settings before the first paint (src/lib/display.ts changes them later; keep the
// keys and values in step). A file, not an inline script, so the site's script-src 'self' policy allows it.
(function () {
  var root = document.documentElement;
  // The page colour of each theme (THEME_COLOR in display.ts), as the theme-color tag the desktop app follows. A
  // reader who follows their device gets no tag, so the app follows the device too.
  var colors = { dark: '#120f33', light: '#f6f1e5' };
  var choice = 'dark';
  try {
    choice = localStorage.getItem('toads-theme') || 'dark';
    var theme = choice;
    if (theme === 'system') theme = matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    root.dataset.theme = theme === 'light' ? 'light' : 'dark';
    if (localStorage.getItem('toads-reading') === 'easy') root.dataset.reading = 'easy';
  } catch (e) {
    root.dataset.theme = 'dark';
  }
  if (choice !== 'system') {
    var meta = document.createElement('meta');
    meta.name = 'theme-color';
    meta.content = colors[root.dataset.theme];
    document.head.appendChild(meta);
  }
})();
