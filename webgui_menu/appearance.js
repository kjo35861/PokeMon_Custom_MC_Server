/* Apply the saved choice before styles paint, shared by both menu destinations. */
(() => {
  'use strict';
  const key = 'pocketmate.theme';
  const valid = value => value === 'light' || value === 'dark';
  let theme = 'dark';
  try {
    const saved = localStorage.getItem(key);
    if (valid(saved)) theme = saved;
  } catch (_) {}
  function apply(value, persist = true) {
    if (!valid(value)) return;
    theme = value;
    document.documentElement.dataset.theme = theme;
    if (persist) {
      try { localStorage.setItem(key, theme); } catch (_) {}
    }
    window.dispatchEvent(new CustomEvent('pocketmate:themechange', {detail: {theme}}));
  }
  window.PocketmateTheme = {get: () => theme, set: value => apply(value)};
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) apply(valid(event.newValue) ? event.newValue : 'dark', false);
  });
  apply(theme, false);
})();
