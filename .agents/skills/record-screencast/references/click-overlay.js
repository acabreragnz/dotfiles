() => {
  if (window.__clickOverlayInstalled) return 'already-installed';
  const css = `
    .__click-marker {
      position: fixed; pointer-events: none;
      width: 48px; height: 48px;
      border: 5px solid #e74c3c; border-radius: 50%;
      transform: translate(-50%, -50%);
      animation: __click-pulse 900ms ease-out forwards;
      z-index: 2147483647;
      box-shadow: 0 0 12px rgba(231,76,60,.6);
    }
    @keyframes __click-pulse {
      0%   { opacity: 1; transform: translate(-50%, -50%) scale(0.3); }
      30%  { opacity: 1; }
      100% { opacity: 0; transform: translate(-50%, -50%) scale(2.4); }
    }

    .__url-banner {
      position: fixed; bottom: 28px; left: 50%;
      transform: translateX(-50%);
      pointer-events: none;
      z-index: 2147483646;
      background: rgba(17, 24, 39, 0.96);
      color: #f9fafb;
      font: 700 18px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
      padding: 12px 22px;
      border-radius: 12px;
      border: 2px solid rgba(96, 165, 250, 0.6);
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
      max-width: 90vw;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      display: flex; align-items: center; gap: 10px;
      transition:
        background 500ms ease-out,
        border-color 500ms ease-out,
        box-shadow 500ms ease-out,
        transform 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    .__url-banner-label {
      display: inline-block;
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: 4px;
      background: rgba(96, 165, 250, 0.18);
      color: #93c5fd;
      font-weight: 700;
      transition: background 400ms ease-out, color 400ms ease-out;
    }
    .__url-banner-from {
      color: #9ca3af;
      text-decoration: line-through;
      text-decoration-color: rgba(156, 163, 175, 0.6);
      font-size: 16px;
      max-width: 30vw;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .__url-banner-arrow {
      color: #fbbf24;
      font-weight: 900;
      font-size: 22px;
      animation: __arrow-slide 900ms ease-in-out infinite;
    }
    @keyframes __arrow-slide {
      0%, 100% { transform: translateX(0); }
      50%      { transform: translateX(4px); }
    }
    .__url-banner-to {
      color: #fff;
    }
    .__url-banner-current {
      color: #f9fafb;
    }

    .__url-banner.__navigating {
      background: #1d4ed8;
      border-color: #fbbf24;
      transform: translateX(-50%) scale(1.12);
      box-shadow:
        0 12px 48px rgba(29, 78, 216, 0.7),
        0 0 0 10px rgba(29, 78, 216, 0.2);
    }
    .__url-banner.__navigating .__url-banner-label {
      background: #fbbf24;
      color: #1f2937;
    }

    .__url-progress {
      position: fixed; top: 0; left: 0;
      height: 4px; width: 0%;
      background: linear-gradient(90deg, #3b82f6, #fbbf24);
      box-shadow: 0 0 12px rgba(59, 130, 246, 0.8);
      pointer-events: none;
      z-index: 2147483647;
      transition: width 800ms ease-out, opacity 400ms ease-out 800ms;
    }
    .__url-progress.__active { width: 100%; opacity: 1; }
    .__url-progress.__done   { width: 100%; opacity: 0; }
  `;
  const s = document.createElement('style');
  s.textContent = css;
  document.head.appendChild(s);

  window.addEventListener('click', (e) => {
    const m = document.createElement('div');
    m.className = '__click-marker';
    m.style.left = e.clientX + 'px';
    m.style.top = e.clientY + 'px';
    document.body.appendChild(m);
    setTimeout(() => m.remove(), 1000);
  }, true);

  const banner = document.createElement('div');
  banner.className = '__url-banner';
  const progress = document.createElement('div');
  progress.className = '__url-progress';

  const pathOf = (href) => {
    try { const u = new URL(href); return u.pathname + u.search + u.hash; }
    catch { return href; }
  };

  const renderIdle = (path) => {
    banner.replaceChildren();
    const label = document.createElement('span');
    label.className = '__url-banner-label';
    label.textContent = 'ON';
    const cur = document.createElement('span');
    cur.className = '__url-banner-current';
    cur.textContent = path;
    banner.appendChild(label);
    banner.appendChild(cur);
    banner.title = location.href;
  };

  const renderNavigating = (fromPath, toPath) => {
    banner.replaceChildren();
    const label = document.createElement('span');
    label.className = '__url-banner-label';
    label.textContent = 'NAVIGATING';
    const from = document.createElement('span');
    from.className = '__url-banner-from';
    from.textContent = fromPath;
    const arrow = document.createElement('span');
    arrow.className = '__url-banner-arrow';
    arrow.textContent = '→';
    const to = document.createElement('span');
    to.className = '__url-banner-to';
    to.textContent = toPath;
    banner.appendChild(label);
    banner.appendChild(from);
    banner.appendChild(arrow);
    banner.appendChild(to);
    banner.title = location.href;
  };

  const STORAGE_KEY = '__rc_lastSeenPath';
  let currentPath = pathOf(location.href);
  let storedPrev = null;
  try { storedPrev = sessionStorage.getItem(STORAGE_KEY); } catch {}
  try { sessionStorage.setItem(STORAGE_KEY, currentPath); } catch {}

  document.body.appendChild(banner);
  document.body.appendChild(progress);

  let lastUrl = location.href;
  let flashTimer = null;

  const startNavigating = (fromPath, toPath) => {
    renderNavigating(fromPath, toPath);
    banner.classList.add('__navigating');
    progress.classList.remove('__active', '__done');
    void progress.offsetWidth;
    progress.classList.add('__active');
    clearTimeout(flashTimer);
    flashTimer = setTimeout(() => {
      banner.classList.remove('__navigating');
      renderIdle(toPath);
      progress.classList.remove('__active');
      progress.classList.add('__done');
    }, 1800);
  };

  if (storedPrev && storedPrev !== currentPath) {
    startNavigating(storedPrev, currentPath);
  } else {
    renderIdle(currentPath);
  }

  setInterval(() => {
    if (location.href !== lastUrl) {
      const fromPath = currentPath;
      const toPath = pathOf(location.href);
      lastUrl = location.href;
      currentPath = toPath;
      try { sessionStorage.setItem(STORAGE_KEY, toPath); } catch {}
      startNavigating(fromPath, toPath);
    } else {
      try { sessionStorage.setItem(STORAGE_KEY, currentPath); } catch {}
    }
    if (!banner.isConnected) document.body.appendChild(banner);
    if (!progress.isConnected) document.body.appendChild(progress);
  }, 200);

  window.__clickOverlayInstalled = true;
  return 'overlay-installed';
}
