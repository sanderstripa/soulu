(() => {
  'use strict';
  const api=window.browserShell,service=window.SouluTranslate;if(!api||!service)return;
  const jobs=new Map(),probes=new Map();let state={},site=null,revision=0,engine=null,activeJob=null,prefs={target:'ru',always:[],never:[]};
  const copy={ru:{title:'Soulu Translate',translate:'Перевести',original:'Показать оригинал',cancel:'Отменить',close:'Закрыть',source:'Язык страницы',target:'Язык перевода',local:'Текст страницы остаётся на устройстве. Модели загружаются один раз.',downloading:'Загрузка языковой модели…',translating:'Перевод страницы…',translated:'Страница переведена',same:'Страница уже на выбранном языке',unsupported:'Эта языковая пара пока не поддерживается',error:'Не удалось перевести страницу. Проверьте сеть при первой загрузке модели и повторите.',always:'Всегда переводить этот язык',never:'Никогда не переводить этот сайт',qr:'QR-код страницы',copy:'Копировать адрес'},en:{title:'Soulu Translate',translate:'Translate',original:'Show original',cancel:'Cancel',close:'Close',source:'Page language',target:'Translate to',local:'Page text stays on your device. Models are downloaded once.',downloading:'Downloading language model…',translating:'Translating page…',translated:'Page translated',same:'The page is already in the selected language',unsupported:'This language pair is not supported yet',error:'Translation failed. Check your connection for the first model download and try again.',always:'Always translate this language',never:'Never translate this site',qr:'Page QR code',copy:'Copy address'}};
  const tr=key=>(copy[state.settings?.language==='en'?'en':'ru'])[key];
  const element=(tag,text)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el;};
  const panel=element('section');panel.className='soulu-translation';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Soulu Translate');document.body.append(panel);
  const key=s=>`${s.tabId}:${s.generation}:${s.url}`;
  const status=element('p');status.setAttribute('role','status');
  const languages={en:{ru:'Английский',en:'English'},ru:{ru:'Русский',en:'Russian'},de:{ru:'Немецкий',en:'German'}};
  function position(){const icon=document.querySelector('.soulu-translate-button');const rect=icon?.getBoundingClientRect();const top=Math.max(8,Math.min((rect?.bottom||48)+8,innerHeight-120));panel.style.top=top+'px';panel.style.maxHeight=Math.max(100,innerHeight-top-12)+'px';}
  window.addEventListener('resize',position);
  function close(){panel.hidden=true;api.setPopover(false,'translation');api.setSuggestionsHeight(0);document.querySelector('.soulu-translate-button')?.focus();}
  function button(text,action){const b=element('button',text);b.type='button';b.onclick=()=>Promise.resolve().then(action).catch(()=>status.textContent=tr('error'));return b;}
  function select(value){const s=element('select');if(value&&!languages[value]){const o=element('option',value);o.value=value;s.append(o);}for(const lang of Object.keys(languages)){const o=element('option',languages[lang][state.settings?.language==='en'?'en':'ru']);o.value=lang;s.append(o);}s.value=value;return s;}
  async function preference(patch){prefs=await api.translation('preferences',{...site,...patch});const detected=probes.get(`${site.tabId}:${site.generation}:${site.url}`);if(detected&&typeof detected==='object'){detected.target=prefs.target;detected.never=(prefs.never||[]).includes(site.origin);}updateIcon();}
  async function restore(job){
    if(!job)return;job.cancelled=true;clearTimeout(job.timer);engine?.cancel(job.key);
    await api.translation('restore',{...job.site,token:job.token});jobs.delete(job.key);
    if(activeJob===job)activeJob=null;status.textContent='';updateIcon();
  }
  async function run(snapshot,from,to){
    service.resolve(from,to);if(service.normalize(from)===service.normalize(to)){status.textContent=tr('same');return;}const id=key(snapshot);await restore(jobs.get(id));
    const {token}=await api.translation('begin',snapshot);
    const job={key:id,site:snapshot,token,from,to,cancelled:false,state:'translating'};jobs.set(id,job);activeJob=job;
    engine??=new service.LocalTranslator(value=>{if(!panel.hidden)status.textContent=tr(value);});
    async function tick(){
      if(job.cancelled||!jobs.has(id))return;
      try{
        const batch=await api.translation('collect',{...snapshot,token});
        if(job.cancelled)return;
        if(batch.nodes.length){
          job.state='translating';if(activeJob===job)status.textContent=tr('translating');
          const rows=await Promise.all(batch.nodes.map(async row=>({id:row.id,text:await engine.translate(from,to,row.text,id)})));
          if(job.cancelled)return;await api.translation('apply',{...snapshot,token,rows});
        }
        if(job.cancelled)return;
        job.state=batch.remaining?'translating':'translated';if(activeJob===job)status.textContent=tr(job.state);updateIcon();
        job.timer=setTimeout(tick,batch.remaining?0:700);
      }catch(error){
        if(job.cancelled)return;job.state='error';if(activeJob===job)status.textContent=tr('error');
        engine?.cancel(id);updateIcon();
      }
    }tick();
  }
  async function open(snapshot=null){
    const ticket=++revision;site=snapshot||await api.getCurrentSite();
    if(ticket!==revision)return;
    const probe=await api.translation('probe',site);const source=jobs.get(key(site))?.from||service.detect(probe.sample,probe.lang);
    prefs=await api.translation('preferences',site);if(ticket!==revision)return;
    panel.classList.remove("soulu-qr");panel.replaceChildren(element('h2',tr('title')));
    const sourceLabel=element('label',tr('source')),from=select(source||'en');sourceLabel.append(from);
    const targetLabel=element('label',tr('target')),to=select(prefs.target||state.settings?.language||'ru');to.querySelector('option[value=de]')?.remove();targetLabel.append(to);
    panel.append(sourceLabel,targetLabel,element('p',tr('local')),status);
    const translate=button(tr('translate'),async()=>{await preference({target:to.value});await run(site,from.value,to.value);});
    panel.append(translate,button(tr('original'),()=>restore(jobs.get(key(site)))),button(tr('cancel'),()=>restore(jobs.get(key(site)))));
    for(const [name,checked] of [['always',(prefs.always||[]).includes(from.value)],['never',(prefs.never||[]).includes(site.origin)]]){
      const label=element('label'),checkbox=element('input');checkbox.type='checkbox';checkbox.checked=checked;
      checkbox.onchange=()=>preference({[name]:checkbox.checked,source:from.value}).catch(()=>status.textContent=tr('error'));
      label.append(checkbox,document.createTextNode(tr(name)));panel.append(label);
    }
    panel.append(button(tr('close'),close));panel.hidden=false;position();api.setPopover(true,'translation');api.setSuggestionsHeight(innerHeight);from.focus();
    const job=jobs.get(key(site));activeJob=job||null;status.textContent=job?tr(job.state):'';
  }
  function updateIcon(){
    const tab=state.tabs?.find(t=>t.id===state.activeTabId);if(!tab)return;
    const host=document.querySelector(state.settings?.layout==='classic'?'.classic-address-pill':'.compact-active-tab');if(!host)return;
    const detected=probes.get(`${tab.id}:${tab.generation}:${tab.url}`);
    const translated=[...jobs.values()].some(j=>j.site.tabId===tab.id);
    const valid=/^https?:|^file:/i.test(tab.url)&&!tab.url.includes('/ui/')&&(translated||(detected?.from&&detected.from!==detected.target&&!detected.never));
    let icon=host.querySelector('.soulu-translate-button');
    if(!valid){icon?.remove();return;}
    if(!icon){icon=element('button');icon.type='button';icon.className='soulu-translate-button';icon.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h12M9 3v2M6 5c0 6 4 10 8 11M13 5c0 6-4 10-8 11M14 21l4-10 4 10M15.5 17h5"/></svg>';icon.onclick=()=>open().catch(()=>{});host.append(icon);}
    icon.title=tr('title');icon.setAttribute('aria-label',tr('title'));icon.dataset.translated=String([...jobs.values()].some(j=>j.site.tabId===tab.id&&j.state==='translated'));
  }
  api.onState(async s=>{
    const old=state.activeTabId,oldPage=state.page;state=s;if(old!==s.activeTabId||oldPage?.generation!==s.page?.generation||oldPage?.url!==s.page?.url){revision++;close();}
    const ids=new Set((s.tabs||[]).map(t=>t.id));
    for(const [id,job] of jobs){const tab=s.tabs?.find(t=>t.id===job.site.tabId);
      if(!ids.has(job.site.tabId)||!tab||tab.url!==job.site.url||tab.generation!==job.site.generation||tab.loading){restore(job).catch(()=>jobs.delete(id));}
    }
    requestAnimationFrame(updateIcon);
    const tab=s.tabs?.find(t=>t.id===s.activeTabId);if(!tab||tab.loading||tab.translationResetting||!/^https?:/i.test(tab.url))return;
    const probeKey=`${tab.id}:${tab.generation}:${tab.url}`;if(probes.has(probeKey))return;probes.set(probeKey,true);if(probes.size>1000)probes.delete(probes.keys().next().value);
    try{const snap=await api.getCurrentSite(),probe=await api.translation('probe',snap),from=service.detect(probe.sample,probe.lang),p=await api.translation('preferences',snap);
      probes.set(probeKey,{from,target:p.target,never:(p.never||[]).includes(snap.origin)});updateIcon();
      if((p.always||[]).includes(from)&&!(p.never||[]).includes(snap.origin)&&from!==p.target)await run(snap,from,p.target);
    }catch{}
  });
  api.onTranslateRequest(async snapshot=>{await open(snapshot);const p=await api.translation('probe',snapshot),from=service.detect(p.sample,p.lang);try{await run(snapshot,from,prefs.target||'ru');}catch{status.textContent=tr('unsupported');}});
  api.onQRRequest(snapshot=>{
    close();if(!/^https?:\/\//i.test(snapshot.url)||typeof window.qrcode!=='function')return;
    const qr=window.qrcode(0,'M');qr.addData(snapshot.url,'Byte');qr.make();const count=qr.getModuleCount(),scale=Math.max(2,Math.floor(240/(count+8)));
    const canvas=element('canvas');canvas.setAttribute('role','img');canvas.setAttribute('aria-label',tr('qr')+': '+snapshot.url);canvas.width=canvas.height=(count+8)*scale;const dc=canvas.getContext('2d');dc.fillStyle='#fff';dc.fillRect(0,0,canvas.width,canvas.height);dc.fillStyle='#000';
    for(let y=0;y<count;y++)for(let x=0;x<count;x++)if(qr.isDark(y,x))dc.fillRect((x+4)*scale,(y+4)*scale,scale,scale);
    panel.replaceChildren(element('h2',tr('qr')),canvas,element('p',snapshot.url),button(tr('copy'),()=>api.shareMenu()),button(tr('close'),close));panel.classList.add('soulu-qr');panel.hidden=false;position();api.setPopover(true,'translation');api.setSuggestionsHeight(innerHeight);
  });
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden){e.preventDefault();close();}});
  document.addEventListener('pointerdown',e=>{if(!panel.hidden&&!panel.contains(e.target)&&!e.target.closest('.soulu-translate-button'))close();});
  window.addEventListener('beforeunload',()=>{engine?.delete();});
  api.getState().then(s=>{state=s;updateIcon();});
})()
