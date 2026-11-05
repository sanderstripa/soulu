export class SouluAppChild extends JSWindowActorChild{
 handleEvent(event){
  if(event.isTrusted&&['mousedown','keydown'].includes(event.type)&&!this.interacted){this.interacted=true;this.sendAsyncMessage('interaction');}
  if(event.type==='mousedown'){if(event.isTrusted){this.gesture={at:Date.now()};this.pointer={screenX:event.screenX,screenY:event.screenY,clientX:event.clientX,clientY:event.clientY};}return;}
  if(event.type==='keydown'){if(event.isTrusted&&['Enter',' '].includes(event.key))this.gesture={at:Date.now()};if(event.isTrusted&&!event.defaultPrevented&&(event.ctrlKey&&(['l','t','w','h','f','r','b',',','+','=','-','0'].includes(event.key.toLowerCase())||!event.shiftKey&&event.key.toLowerCase()==='j'||event.shiftKey&&['Delete','o','O'].includes(event.key))||['F5','F9'].includes(event.key)||event.altKey&&['ArrowLeft','ArrowRight','f','F','t','T'].includes(event.key))){event.preventDefault();this.sendAsyncMessage('accelerator',{key:event.key,ctrlKey:event.ctrlKey,shiftKey:event.shiftKey,altKey:event.altKey,metaKey:event.metaKey});}return;}
  if(event.type!=='SouluRequest'||typeof event.detail!=='string')return;let input;try{input=JSON.parse(event.detail);}catch{return;}if(!Number.isSafeInteger(input.id)||typeof input.request!=='string')return;
  this.sendQuery('dispatch',{...input,pointer:this.pointer,userGesture:this.gesture}).then(value=>this.respond({id:input.id,value}),error=>this.respond({id:input.id,error:String(error.message||error)}));
 }
 async receiveMessage(message){
  if(message.name==='preparePresentation'){const win=this.contentWindow;win.document.documentElement.getBoundingClientRect();win.windowUtils.updateLayerTree();return true;}
  if(message.name==='extensionAnchor'){
   const win=this.contentWindow,id=String(message.data),node=win.document.querySelector('[data-extension-toolbar="classic"] [data-extension-id="'+win.CSS.escape(id)+'"]');const target=node||win.document.querySelector('#soulu-extensions-menu');if(!target)return null;const r=target.getBoundingClientRect();return r.width&&r.height?{x:r.x,y:r.y,width:r.width,height:r.height}:null;
  }
  if(message.name==='testing'){
   if(Services.env.get('SOULU_GECKO_TEST')!=='1')throw Error('Test harness is disabled');
   const win=this.contentWindow.wrappedJSObject,sandbox=Cu.Sandbox(win,{sandboxPrototype:win,wantXrays:false});return await Cu.evalInSandbox('(async()=>{'+message.data+'})()',sandbox);
  }
  if(message.name==='emit'||message.name==='home'){const data=message.name==='home'?{name:'home',value:message.data}:message.data;this.contentWindow.dispatchEvent(new this.contentWindow.CustomEvent('SouluEmit',{detail:JSON.stringify(data)}));}
  if(message.name==='openSection'){const settings=this.contentWindow.wrappedJSObject.souluSettings;if(settings){await settings.reload();settings.openSection(message.data);}}
 }
 respond(value){try{this.contentWindow.dispatchEvent(new this.contentWindow.CustomEvent('SouluResponse',{detail:JSON.stringify(value)}));}catch{}}
}
