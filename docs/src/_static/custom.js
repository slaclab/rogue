function pruneApiAnchorLinks() {
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
}

function getDocsConfig() {
  return window.ROGUE_DOCS || {};
}

function normalizeSiteRoot(siteRoot) {
  if (!siteRoot || siteRoot === '/') {
    return '';
  }

  return siteRoot.endsWith('/') ? siteRoot.slice(0, -1) : siteRoot;
}

function splitRelativePath(pathname, siteRoot) {
  if (siteRoot && pathname.startsWith(`${siteRoot}/`)) {
    return pathname.slice(siteRoot.length + 1).split('/').filter(Boolean);
  }

  if (siteRoot && pathname === siteRoot) {
    return [];
  }

  return pathname.split('/').filter(Boolean);
}

function joinUrl(siteRoot, ...parts) {
  const normalizedRoot = normalizeSiteRoot(siteRoot);
  const segments = [];

  if (normalizedRoot) {
    segments.push(normalizedRoot.replace(/^\/+/, ''));
  }

  for (const part of parts) {
    if (!part) {
      continue;
    }
    segments.push(part.replace(/^\/+|\/+$/g, ''));
  }

  return `/${segments.join('/')}/`;
}

function getVersionsUrl(siteRoot) {
  return siteRoot ? `${siteRoot}/versions.json` : '/versions.json';
}

function detectCurrentVersion(pathname, siteRoot, versions) {
  const entries = new Set(versions.map((entry) => entry.slug));
  const parts = splitRelativePath(pathname, siteRoot);
  if (!parts.length) {
    return null;
  }

  return entries.has(parts[0]) ? parts[0] : null;
}

function relativePagePath(pathname, siteRoot, currentVersion) {
  if (!currentVersion) {
    return '';
  }

  const parts = splitRelativePath(pathname, siteRoot);
  if (!parts.length || parts[0] !== currentVersion) {
    return '';
  }

  return parts.slice(1).join('/');
}

function entryForSlug(metadata, slug) {
  return metadata.versions.find((entry) => entry.slug === slug) || null;
}

function createBanner(text, href, linkText) {
  const container = document.querySelector('.wy-nav-content');
  if (!container || container.querySelector('.rogue-docs-banner')) {
    return;
  }

  const banner = document.createElement('div');
  banner.className = 'rogue-docs-banner';
  banner.textContent = `${text} `;

  if (href && linkText) {
    const link = document.createElement('a');
    link.href = href;
    link.textContent = linkText;
    banner.appendChild(link);
  }

  container.prepend(banner);
}

function renderBanner(metadata, currentVersion, siteRoot) {
  if (!currentVersion) {
    return;
  }

  if (currentVersion === 'pre-release') {
    createBanner(
      'You are viewing unreleased documentation from pre-release.',
      entryForSlug(metadata, metadata.default)?.url || joinUrl(siteRoot, metadata.default),
      'Open latest release.',
    );
    return;
  }

  const currentEntry = entryForSlug(metadata, currentVersion);
  if (!currentEntry || currentEntry.kind !== 'release') {
    return;
  }

  const newestRelease = metadata.versions.find((entry) => entry.kind === 'release');
  if (newestRelease && newestRelease.slug === currentVersion) {
    return;
  }

  createBanner(
    `You are viewing archived documentation for ${currentVersion}.`,
    entryForSlug(metadata, metadata.default)?.url || joinUrl(siteRoot, metadata.default),
    'Open latest release.',
  );
}

async function urlExists(url) {
  try {
    const response = await fetch(url, {
      method: 'HEAD',
      cache: 'no-store',
    });
    return response.ok;
  }
  catch (error) {
    return false;
  }
}

function renderVersionSelector(metadata, currentVersion, siteRoot) {
  const switcher = document.querySelector('[data-rogue-version-switcher]');
  if (!switcher) {
    return null;
  }

  const select = switcher.querySelector('select');
  const allVersions = switcher.querySelector('[data-rogue-all-versions]');
  if (!select || !allVersions) {
    return null;
  }

  select.innerHTML = '';

  for (const entry of metadata.versions) {
    const option = document.createElement('option');
    option.value = entry.slug;
    option.textContent = entry.title;
    option.selected = entry.slug === currentVersion;
    select.appendChild(option);
  }

  if (!currentVersion && metadata.versions.length > 0) {
    select.selectedIndex = 0;
  }

  allVersions.href = joinUrl(siteRoot, 'versions');
  switcher.hidden = false;

  return select;
}

async function handleVersionChange(event, metadata, currentVersion, siteRoot) {
  const targetVersion = event.target.value;
  const targetEntry = entryForSlug(metadata, targetVersion);
  if (!targetEntry) {
    return;
  }

  const relativePath = relativePagePath(window.location.pathname, siteRoot, currentVersion);
  let targetUrl = targetEntry.url;

  if (relativePath) {
    const pageUrl = joinUrl(siteRoot, targetVersion, relativePath);
    if (await urlExists(pageUrl)) {
      targetUrl = pageUrl;
    }
  }

  window.location.href = `${targetUrl}${window.location.search}${window.location.hash}`;
}

async function initVersionUi() {
  const siteRoot = normalizeSiteRoot(getDocsConfig().siteRoot || '');
  const switcher = document.querySelector('[data-rogue-version-switcher]');
  if (!switcher) {
    return;
  }

  try {
    const response = await fetch(getVersionsUrl(siteRoot), { cache: 'no-store' });
    if (!response.ok) {
      return;
    }

    const metadata = await response.json();
    if (!Array.isArray(metadata.versions) || metadata.versions.length === 0) {
      return;
    }

    const currentVersion = detectCurrentVersion(window.location.pathname, siteRoot, metadata.versions);
    renderBanner(metadata, currentVersion, siteRoot);

    const select = renderVersionSelector(metadata, currentVersion, siteRoot);
    if (!select) {
      return;
    }

    select.addEventListener('change', (event) => {
      void handleVersionChange(event, metadata, currentVersion, siteRoot);
    });
  }
  catch (error) {
    // Keep docs usable even when version metadata is unavailable.
  }
}

document.addEventListener('DOMContentLoaded', () => {
  pruneApiAnchorLinks();
  void initVersionUi();
});
