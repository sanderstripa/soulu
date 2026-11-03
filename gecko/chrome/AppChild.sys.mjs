export class SouluAppChild extends JSWindowActorChild{
 handleEvent(event){
  if(event.type==='mousedown'){if(event.isTrusted)this.pointer={screenX:event.screenX,screenY:event.screenY,clientX:event.clientX,clientY:event.clientY};return;}
  if(event.type==='keydown'){if(event.isTrusted&&event.ctrlKey&&['l','t','w','h'].includes(event.key.toLowerCase())){event.preventDefault();this.sendAsyncMessage('accelerator',{key:event.key,ctrlKey:true,shiftKey:event.shiftKey});}return;}
  if(event.type!=='SouluRequest'||typeof event.detail!=='string')return;let input;try{input=JSON.parse(event.detail);}catch{return;}if(!Number.isSafeInteger(input.id)||typeof input.request!=='string')return;
  this.sendQuery('dispatch',{...input,pointer:this.pointer}).then(value=>this.respond({id:input.id,value}),error=>this.respond({id:input.id,error:String(error.message||error)}));
 }
 async receiveMessage(message){
  if(message.name==='testing'){
   if(Services.env.get('SOULU_GECKO_TEST')!=='1')throw Error('Test harness is disabled');
   const win=this.contentWindow.wrappedJSObject,sandbox=Cu.Sandbox(win,{sandboxPrototype:win,wantXrays:false});return await Cu.evalInSandbox('(async()=>{'+message.data+'})()',sandbox);
  }
  if(message.name==='emit'||message.name==='home'){const data=message.name==='home'?{name:'home',value:message.data}:message.data;this.contentWindow.dispatchEvent(new this.contentWindow.CustomEvent('SouluEmit',{detail:JSON.stringify(data)}));}
  if(message.name==='openSection')this.contentWindow.wrappedJSObject.souluSettings?.openSection(message.data);
 }
 respond(value){try{this.contentWindow.dispatchEvent(new this.contentWindow.CustomEvent('SouluResponse',{detail:JSON.stringify(value)}));}catch{}}
}
