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
  window.__clickOverlayInstalled = true;
  return 'overlay-installed';
}
