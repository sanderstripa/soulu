  const scrollArea = el('div', 'bookmark-scroll-area');
  const thumb = el('div', 'bookmark-scroll-thumb');
  thumb.setAttribute('aria-hidden', 'true');
  scrollArea.append(contents, thumb);
  menu.append(menuHeading, menuSearch, scrollArea, actions);

  function updateThumb() {
    const height = contents.clientHeight;
    const range = contents.scrollHeight - height;
    thumb.hidden = range <= 0 || height === 0;
    scrollArea.toggleAttribute('data-overflow', !thumb.hidden);
    if (thumb.hidden) return;
    const size = Math.min(height, Math.max(24, height * height / contents.scrollHeight));
    thumb.style.height = size + 'px';
    thumb.style.transform = 'translateY(' + (height - size) * contents.scrollTop / range + 'px)';
  }
  new ResizeObserver(updateThumb).observe(contents);
  new MutationObserver(updateThumb).observe(contents, { childList: true, subtree: true });
  contents.addEventListener('scroll', updateThumb, { passive: true });
  let dragOffset = 0;
  thumb.onpointerdown = event => {
    if (event.button !== 0) return;
    dragOffset = event.clientY - thumb.getBoundingClientRect().top;
    thumb.setPointerCapture(event.pointerId);
    event.preventDefault();
  };
  thumb.onpointermove = event => {
    if (!thumb.hasPointerCapture(event.pointerId)) return;
    const travel = contents.clientHeight - thumb.offsetHeight;
    if (travel > 0) contents.scrollTop = (event.clientY - scrollArea.getBoundingClientRect().top - dragOffset)
      * (contents.scrollHeight - contents.clientHeight) / travel;
  };
