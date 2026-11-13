import {adblock} from 'chrome://sona/content/adblock.sys.mjs';
export class SonaCosmeticParent extends JSWindowActorParent{
 async receiveMessage(message){if(message.name!=='selectors')return [];const url=this.manager.documentPrincipal.URI?.spec||'';if(!/^https?:/.test(url))return [];const input=message.data||{};return adblock.cosmetic(url,{classes:Array.isArray(input.classes)?input.classes.filter(v=>typeof v==='string'&&v.length<256).slice(0,256):[],ids:Array.isArray(input.ids)?input.ids.filter(v=>typeof v==='string'&&v.length<256).slice(0,256):[]});}
}
