document.addEventListener('DOMContentLoaded', () => {
  if (!window.location.pathname.includes('/api/')) {
    return;
  }

  const nav = document.querySelector('.wy-menu.wy-menu-vertical');
  if (!nav) {
    return;
  }

  for (const link of nav.querySelectorAll('a[href*="#"]')) {
    const href = link.getAttribute('href');
    if (!href || href === '#') {
      continue;
    }

    const item = link.closest('li');
    if (item) {
      item.remove();
    }
  }

  let changed = true;
  while (changed) {
    changed = false;

    for (const node of nav.querySelectorAll('ul, li')) {
      if (node.matches('ul') && node.children.length === 0) {
        node.remove();
        changed = true;
        continue;
      }

      if (node.matches('li')) {
        const directLink = node.querySelector(':scope > a');
        const directList = node.querySelector(':scope > ul');
        if (!directLink && !directList) {
          node.remove();
          changed = true;
        }
      }
    }
  }
});
