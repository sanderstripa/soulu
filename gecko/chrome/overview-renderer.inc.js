function renderOverview(){
 if(overview.hidden)return;const q=search.value.toLocaleLowerCase(),tabs=(state.tabs||[]).filter(t=>(t.title+' '+t.url).toLocaleLowerCase().includes(q));
 const signature=JSON.stringify([q,tabs.map(t=>[t.id,t.title,t.url,t.favicon,t.active,t.thumbnail])]);if(signature===overviewSignature)return;overviewSignature=signature;
 const existing=new Map([...grid.querySelectorAll('[data-overview-id]')].map(n=>[Number(n.dataset.overviewId),n]));let index=0;
 for(const tab of tabs){let card=existing.get(tab.id);if(!card){card=el('article','overview-card');card.dataset.overviewId=tab.id;const preview=button('',async()=>{await api.switchTab(tab.id);await api.setOverview(false);});preview.classList.add('overview-preview');const caption=el('div','overview-caption'),title=el('span','overview-title'),close=button('×',()=>api.closeTab(tab.id));caption.append(icon(tab),title,close);card.append(preview,caption);}
  existing.delete(tab.id);card.classList.toggle('active',!!tab.active);const preview=card.firstElementChild,caption=card.lastElementChild,title=tab.title||'Новая вкладка';preview.setAttribute('aria-label',title);caption.querySelector('.overview-title').textContent=title;caption.lastElementChild.setAttribute('aria-label','Закрыть '+title);
  const imageKey=String(tab.favicon||'')+'|'+title;if(card.iconKey!==imageKey){caption.firstElementChild.replaceWith(icon(tab));card.iconKey=imageKey;}
  if(card.thumbnail!==tab.thumbnail){card.thumbnail=tab.thumbnail;preview.replaceChildren();if(tab.thumbnail){const image=el('img');image.src=tab.thumbnail;image.alt='';preview.append(image);}else preview.append(el('span','preview-placeholder','Превью появится после просмотра вкладки'));}
  if(grid.children[index]!==card)grid.insertBefore(card,grid.children[index]||null);index++;
 }
 for(const node of existing.values())node.remove();let add=grid.querySelector('.overview-new');if(!add){add=button('+ Новая вкладка',async()=>{await api.newTab();await api.setOverview(false);});add.classList.add('overview-new');grid.append(add);}if(grid.lastElementChild!==add)grid.append(add);
}
