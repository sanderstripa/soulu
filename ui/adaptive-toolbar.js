/* Native geometry ticks animate the toolbar and the existing page together. */
(() => {
  const toolbar = document.querySelector('.classic-toolbar');
  const row = toolbar.querySelector('.tabs-zone');
  let animationToken = 0, animationEnd = 0;
  function render(frame) {
    if (document.body.dataset.layout !== 'adaptive' || !frame) return;
    const progress = Math.max(0, Math.min(1, Number(frame.progress) || 0));
    document.body.style.setProperty('--adaptive-progress', String(progress));
    document.body.style.setProperty('--adaptive-toolbar-height', `${frame.height}px`);
    document.body.dataset.adaptiveExpanded = String(!!frame.expanded);
    row.style.visibility = progress <= 0 ? 'hidden' : '';
    row.inert = !frame.expanded || progress <= 0;
    row.setAttribute('aria-hidden', String(!frame.expanded));
    if (!frame.expanded && row.contains(document.activeElement)) {
      document.querySelector('#classicAddress')?.focus({preventScroll:true});
    }
    // Popups must follow the address capsule while it moves.
    const box = document.querySelector('#classicAddress')?.closest('form')?.addressSuggestions;
    if (box?.classList.contains('visible')) box.positionForAddress?.();
  }
  function apply(frame) {
    if (frame?.animation) {
      const {startAt,duration,from,to} = frame.animation;
      const token = ++animationToken;
      animationEnd = startAt + duration;
      const tick = () => {
        if (token !== animationToken) return;
        const p = Math.max(0,Math.min(1,(Date.now()-startAt)/duration));
        const height = from+(to-from)*(1-Math.pow(1-p,3));
        render({expanded:frame.expanded,progress:(height-68)/20,height});
        if (p<1) requestAnimationFrame(tick);
        else animationEnd=0;
      };
      requestAnimationFrame(tick);
    } else if (Date.now()>=animationEnd) render(frame);
  }
  function sync(state) {
    if (state.settings?.layout !== 'adaptive') {
      row.inert = false;
      row.style.visibility = '';
      row.removeAttribute('aria-hidden');
      return;
    }
    const expanded = state.tabs.length > 1;
    apply(state.adaptiveToolbar?.active ? state.adaptiveToolbar : {expanded,progress:expanded?1:0,height:expanded?88:68});
  }
  window.sonaAdaptiveToolbar = {sync};
  window.browserShell.onAdaptiveGeometry?.(apply);
})();
