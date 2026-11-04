// Only explicitly linked Soulu pages run this; never inject into web content.
// Hold the first visible frame until all real faces are available, including Cyrillic.
window.souluTypographyReady = Promise.all([400,500,600].map(weight =>
  document.fonts.load(`${weight} 14px Onest`, 'Aa Ёё Йй Жж Щщ Ыы Дд Лл 0123456789 @/:;()[]—+%')
)).then(faces => {
  if (faces.some(face => !face.length)) throw new Error('Bundled Onest face unavailable');
  document.documentElement.classList.add('typography-ready');
  return true;
}).catch(error => {
  // A broken package must not quietly present a different UI font.
  console.error('Soulu typography initialization failed', error);
  document.documentElement.dataset.typographyError = String(error);
  throw error;
});

// Native title bubbles cannot select a page's private @font-face. Own pages
// use one semantic tooltip and ARIA; never leave a competing native title.
const souluNormalizeTitles=root=>{
  const nodes=[...(root.matches?.('[title]')?[root]:[]),...root.querySelectorAll('[title]')];
  for(const node of nodes){const title=node.getAttribute('title');if(title){if(node.dataset.tooltip!==title)node.dataset.tooltip=title;if(!node.textContent.trim()&&(!node.getAttribute('aria-label')||node.getAttribute('aria-label')===node.dataset.tooltipLabel)){if(node.getAttribute('aria-label')!==title)node.setAttribute('aria-label',title);if(node.dataset.tooltipLabel!==title)node.dataset.tooltipLabel=title;}}node.removeAttribute('title');}
};
souluNormalizeTitles(document);
new MutationObserver(records=>{const roots=new Set();for(const r of records){if(r.type==='attributes'){if(r.target.hasAttribute('title'))roots.add(r.target);}else for(const node of r.addedNodes)if(node.nodeType===1)roots.add(node);}for(const root of roots)if(root.isConnected)souluNormalizeTitles(root);}).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['title']});
(() => {
  const tip=document.createElement('div');tip.className='soulu-type-tooltip';
  tip.id='soulu-type-tooltip';tip.setAttribute('role','tooltip');tip.hidden=true;
  document.body.append(tip);
  let owner=null,timer=0,previousDescription=null,expanded=false;
  const hide=()=>{
    clearTimeout(timer);tip.hidden=true;
    if(expanded){expanded=false;if(!document.querySelector('.suggestions.visible'))window.browserShell?.setSuggestionsHeight(0);}
    if(owner){if(previousDescription===null)owner.removeAttribute('aria-describedby');else owner.setAttribute('aria-describedby',previousDescription);}
    owner=null;
  };
  const show=(node)=>{
    if(!node||node===owner||node.closest('.reader-article'))return;
    hide();owner=node;previousDescription=node.getAttribute('aria-describedby');
    timer=setTimeout(()=>{
      const label=node.dataset.tooltip||node.title;if(!node.isConnected||!label)return hide();
      tip.textContent=label;tip.hidden=false;
      const r=node.getBoundingClientRect(),size=tip.getBoundingClientRect();
      tip.style.left=Math.max(8,Math.min(r.left,innerWidth-size.width-8))+'px';
      const below=r.bottom+8;
      const toolbar=!!node.closest('.browser-toolbar');
      tip.style.top=(toolbar?below:(below+size.height+8<=innerHeight?below:Math.max(8,r.top-size.height-8)))+'px';
      if(toolbar){expanded=true;window.browserShell?.setSuggestionsHeight(Math.ceil(below+size.height+8));}
      node.setAttribute('aria-describedby',[previousDescription,tip.id].filter(Boolean).join(' '));
    },420);
  };
  document.addEventListener('pointerover',event=>show(event.target.closest('[title],[data-tooltip]')));
  document.addEventListener('pointerout',event=>{if(owner&&!owner.contains(event.relatedTarget))hide();});
  document.addEventListener('focusin',event=>show(event.target.closest('[title],[data-tooltip]')));
  document.addEventListener('focusout',hide);
  document.addEventListener('pointerdown',hide);
  document.addEventListener('keydown',hide);
  document.addEventListener('scroll',hide,true);
  window.addEventListener('resize',()=>{if(!expanded)hide();});
  window.addEventListener('blur',hide);
})();

(()=>{
 const script=document.createElement('script');script.src=new URL('select-control.js',document.currentScript.src).href;script.async=false;
 window.souluSelectReady=new Promise((resolve,reject)=>{script.onload=()=>Promise.resolve(window.souluSelectControlsReady).then(resolve,reject);script.onerror=()=>reject(Error('Soulu controls could not be loaded'));});
 window.souluSelectReady.catch(error=>console.error('Soulu controls:',error));document.head.append(script);
})();
