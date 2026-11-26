// Executes in the document's main frame. Return measurements, never page prose.
({targets, initial}) => {
  const state = window.__ahObserver ??= {nodes: new Map(), occurrences: new Map()};
  const candidates = new Map();
  for (const t of targets) {
    for (const el of document.querySelectorAll(t.selector)) candidates.set(el, t.name);
  }
  const markers = '[data-ad-slot],[data-ad-unit],[data-google-query-id],ins.adsbygoogle,[id^="div-gpt-ad"]';
  for (const el of document.querySelectorAll(markers)) {
    if (!candidates.has(el) && ![...candidates.keys()].some(parent => parent.contains(el))) candidates.set(el, null);
  }
  function inView(r) {
    return r.width > 0 && r.height > 0 && r.top < innerHeight && r.bottom > 0 && r.left < innerWidth && r.right > 0;
  }
  function displayed(el) {
    return el.checkVisibility({opacityProperty:true, visibilityProperty:true});
  }
  for (const [el, expected] of candidates) {
    if (state.nodes.size >= 200 && !state.nodes.has(el)) continue;
    if (!state.nodes.has(el)) {
      const base = String(expected || el.getAttribute('data-ad-slot') || el.getAttribute('data-ad-unit') || el.id || el.tagName).slice(0,120);
      const identity = JSON.stringify([expected ? 'profile' : 'marker', base]);
      const n = (state.occurrences.get(identity) || 0) + 1;
      state.occurrences.set(identity, n);
      state.nodes.set(el, {name: n === 1 ? base : base + ' (' + n + ')', key: JSON.stringify([identity,n]), expected,
        seen:false, visibleMedia:false, frame:false, initialInView:false, initialMedia:false});
    }
    const p = state.nodes.get(el);
    const box = el.getBoundingClientRect();
    const seen = inView(box) && displayed(el);
    const media = [...el.querySelectorAll('img,video,canvas')].filter(node => {
      const r = node.getBoundingClientRect();
      if (r.width <= 2 || r.height <= 2 || !displayed(node)) return false;
      if (node.tagName === 'IMG') return node.complete && node.naturalWidth > 2;
      if (node.tagName === 'VIDEO') return node.readyState >= 2;
      return node.width > 2 && node.height > 2;
    });
    if (initial) { p.initialInView = seen; p.initialMedia = media.length > 0; }
    p.seen ||= seen;
    p.visibleMedia ||= seen && media.some(node => inView(node.getBoundingClientRect()));
    p.frame ||= el.tagName === 'IFRAME' || !!el.querySelector('iframe');
  }
  return {slots:[...state.nodes.values()], bottom:scrollY + innerHeight >= document.documentElement.scrollHeight - 2,
    capped:state.nodes.size >= 200};
}
