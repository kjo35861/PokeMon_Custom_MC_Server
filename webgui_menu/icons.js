(() => {
  'use strict';
  const names=new Set(["ball", "home", "land", "vault", "users", "history", "trash", "book", "bag", "flag", "compass", "warp", "arrow", "up", "down", "x", "leaf", "spark", "gear", "target", "plus", "minus", "check", "info", "edit"]);
  window.PocketmateIcons=name=>names.has(name)?`<svg class="pm-icon" aria-hidden="true" focusable="false"><use href="#i-${name}"/></svg>`:'';
})();
