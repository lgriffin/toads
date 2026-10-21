// Applies the reader's saved display settings before the first paint (src/lib/display.ts changes them later; keep the
// keys and values in step). A file, not an inline script, so the site's script-src 'self' policy allows it.
(function () {
  var root = document.documentElement;
  try {
    var theme = localStorage.getItem('toads-theme');
    if (theme === 'system') theme = matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    root.dataset.theme = theme === 'light' ? 'light' : 'dark';
    if (localStorage.getItem('toads-reading') === 'easy') root.dataset.reading = 'easy';
  } catch (e) {
    root.dataset.theme = 'dark';
  }
})();
