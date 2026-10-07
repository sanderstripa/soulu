/* Supply actual DOM bounds, never a second set of caption size assumptions. */
(() => {
  if (!window.browserShell?.setCaptionBounds) return;
  let pending = false, previous = '';
  function update() {
    pending = false;
    const node = document.body.dataset.layout === 'classic' ?
      document.querySelector('#windowMaximize') : document.querySelector('#compactWindowMaximize');
    const r = node?.getClientRects().length ? node.getBoundingClientRect() : null;
    const rect = r ? {x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)} : {x:0,y:0,width:0,height:0};
    const serialized = JSON.stringify(rect);
    if (serialized !== previous) {
      previous = serialized;
      window.browserShell.setCaptionBounds(rect).catch(() => { previous = ''; });
    }
  }
  function schedule() { if (!pending) { pending = true; requestAnimationFrame(update); } }
  new MutationObserver(schedule).observe(document.body,{attributes:true});
  const observer = new ResizeObserver(schedule);
  document.querySelectorAll('.browser-toolbar').forEach(node => observer.observe(node));
  window.addEventListener('resize',schedule);
  schedule();
})();
