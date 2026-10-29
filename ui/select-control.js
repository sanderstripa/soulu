window.souluSelectControlsReady=(async()=>{
const stylesheet=document.createElement('link');stylesheet.rel='stylesheet';stylesheet.href=new URL('select-control.css',document.currentScript.src).href;document.head.append(stylesheet);await new Promise(resolve=>{stylesheet.onload=resolve;stylesheet.onerror=resolve});
const controls=new WeakMap();
let sequence=0;
function enhance(select){
 if(controls.has(select)||select.multiple||select.size>1)return;
 const wrap=document.createElement('span'),button=document.createElement('button'),label=document.createElement('span'),arrow=document.createElement('span'),menu=document.createElement('div');
 wrap.className='soulu-select';button.type='button';button.className='soulu-select-button';label.className='soulu-select-label';arrow.className='soulu-select-arrow';arrow.setAttribute('aria-hidden','true');menu.className='soulu-select-menu';menu.id='soulu-select-'+(++sequence);menu.setAttribute('popover','auto');menu.setAttribute('role','listbox');button.setAttribute('aria-haspopup','listbox');button.setAttribute('aria-controls',menu.id);button.setAttribute('aria-expanded','false');
 select.before(wrap);wrap.append(select,button);button.append(label,arrow);(select.closest('dialog')||document.body).append(menu);select.classList.add('soulu-select-source');select.tabIndex=-1;select.setAttribute('aria-hidden','true');
 let active=0,search='',searchTimer=0;
 const options=()=>[...select.options];
 function sync(){label.textContent=select.selectedOptions[0]?.label||'';button.disabled=select.disabled;button.setAttribute('aria-label',select.getAttribute('aria-label')||select.labels?.[0]?.textContent||label.textContent);wrap.hidden=select.hidden;}
 function position(){const r=button.getBoundingClientRect();menu.style.width=Math.min(Math.max(r.width,160),innerWidth-16)+'px';const h=Math.min(menu.scrollHeight,280,innerHeight-20),below=innerHeight-r.bottom-8;menu.style.maxHeight=Math.max(60,Math.min(280,below>=Math.min(h,100)?below:r.top-8))+'px';menu.style.left=Math.max(8,Math.min(r.left,innerWidth-menu.offsetWidth-8))+'px';const desired=below>=Math.min(h,100)?r.bottom+6:r.top-menu.offsetHeight-6;menu.style.top=Math.max(8,Math.min(innerHeight-menu.offsetHeight-8,desired))+'px';}
 function highlight(index){const rows=[...menu.children];if(!rows.length)return;active=Math.max(0,Math.min(rows.length-1,index));for(let i=0;i<rows.length;i++)rows[i].classList.toggle('highlighted',i===active);button.setAttribute('aria-activedescendant',rows[active].id);rows[active].scrollIntoView({block:'nearest'});}
 function choose(index){const option=options()[index];if(!option||option.disabled)return;const changed=select.selectedIndex!==index;select.selectedIndex=index;sync();menu.hidePopover();button.focus({preventScroll:true});if(changed){select.dispatchEvent(new Event('input',{bubbles:true}));select.dispatchEvent(new Event('change',{bubbles:true}));}}
 function open(){if(button.disabled)return;menu.replaceChildren();options().forEach((o,i)=>{const row=document.createElement('div');row.id=menu.id+'-'+i;row.className='soulu-select-option';row.setAttribute('role','option');row.setAttribute('aria-selected',String(o.selected));row.setAttribute('aria-disabled',String(o.disabled));row.textContent=o.label;row.onpointermove=()=>{if(!o.disabled)highlight(i)};row.onmousedown=e=>e.preventDefault();row.onclick=()=>choose(i);menu.append(row)});menu.showPopover();position();highlight(Math.max(0,select.selectedIndex));}
 button.onclick=()=>menu.matches(':popover-open')?menu.hidePopover():open();
 button.onkeydown=e=>{if(['ArrowDown','ArrowUp','Home','End','Enter',' ','Escape'].includes(e.key)){e.preventDefault();if(e.key==='Escape'){if(menu.matches(':popover-open'))menu.hidePopover();return;}if(!menu.matches(':popover-open')){open();return;}if(e.key==='Enter'||e.key===' '){choose(active);return;}const rows=options();let next=e.key==='Home'?0:e.key==='End'?rows.length-1:active+(e.key==='ArrowDown'?1:-1);while(rows[next]?.disabled)next+=e.key==='ArrowUp'?-1:1;highlight(next);}else if(e.key.length===1&&!e.ctrlKey&&!e.metaKey){clearTimeout(searchTimer);search+=e.key.toLocaleLowerCase();searchTimer=setTimeout(()=>search='',700);if(!menu.matches(':popover-open'))open();const i=options().findIndex(o=>!o.disabled&&o.label.toLocaleLowerCase().startsWith(search));if(i>=0)highlight(i);}};
 menu.addEventListener('toggle',()=>{const shown=menu.matches(':popover-open');button.setAttribute('aria-expanded',String(shown));if(!shown)button.removeAttribute('aria-activedescendant');});
 select.addEventListener('change',sync);select.addEventListener('focus',()=>button.focus({preventScroll:true}));
 const descriptor=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value');Object.defineProperty(select,'value',{configurable:true,get(){return descriptor.get.call(this)},set(v){descriptor.set.call(this,v);sync()}});
 const observer=new MutationObserver(sync);observer.observe(select,{attributes:true,childList:true,subtree:true});controls.set(select,{sync,menu,observer});sync();
}
function scan(){for(const select of document.querySelectorAll('select'))enhance(select);for(const menu of document.querySelectorAll('.soulu-select-menu'))if(!document.querySelector('[aria-controls="'+menu.id+'"]'))menu.remove();}
new MutationObserver(scan).observe(document.documentElement,{childList:true,subtree:true});scan();
window.addEventListener('resize',()=>{for(const menu of document.querySelectorAll('.soulu-select-menu:popover-open'))menu.hidePopover()});
document.addEventListener('scroll',e=>{for(const menu of document.querySelectorAll('.soulu-select-menu:popover-open'))if(!menu.contains(e.target))menu.hidePopover()},true);

document.addEventListener('focusin',e=>{for(const menu of document.querySelectorAll('.soulu-select-menu:popover-open')){const button=document.querySelector('[aria-controls="'+menu.id+'"]');if(e.target!==button&&!menu.contains(e.target))menu.hidePopover()}});

})();
