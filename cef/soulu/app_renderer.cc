#include "examples/soulu/video_renderer.h"
#include "examples/soulu/app_factory.h"
#include "examples/soulu/page_glass_script.h"
#include "include/wrapper/cef_message_router.h"
#include "include/cef_parser.h"
#include "include/cef_process_message.h"
#include <set>
#include "examples/soulu/adblock_cosmetic.h"

namespace soulu {
class PageScrollSubmit final : public CefV8Handler {
 public:
  bool Execute(const CefString&,CefRefPtr<CefV8Value>,const CefV8ValueList& args,CefRefPtr<CefV8Value>&,CefString&) override {
    auto c=CefV8Context::GetCurrentContext();if(!c||!c->GetFrame()->IsMain()||args.size()!=1||!args[0]->IsDouble())return true;
    auto message=CefProcessMessage::Create("soulu.page.scroll");message->GetArgumentList()->SetDouble(0,args[0]->GetDoubleValue());
    c->GetFrame()->SendProcessMessage(PID_BROWSER,message);return true;
  }
 private: IMPLEMENT_REFCOUNTING(PageScrollSubmit);
};
class MediaSubmit final : public CefV8Handler {
 public:
  bool Execute(const CefString& name,CefRefPtr<CefV8Value>,const CefV8ValueList& args,CefRefPtr<CefV8Value>&,CefString&) override {
    auto context=CefV8Context::GetCurrentContext();if(!context)return true;
    auto frame=context->GetFrame();auto message=CefProcessMessage::Create(name=="fill"?"soulu.credential.fill":"soulu.media.playback");
    if(name=="fill"){
      if(!frame->IsMain()||args.size()!=2||!args[0]->IsInt()||!args[1]->IsInt())return true;
      message->GetArgumentList()->SetInt(0,args[0]->GetIntValue());message->GetArgumentList()->SetInt(1,args[1]->GetIntValue());
    }else {if(args.size()!=1||!args[0]->IsBool())return true;message->GetArgumentList()->SetBool(0,args[0]->GetBoolValue());}
    frame->SendProcessMessage(PID_BROWSER,message);return true;
  }
 private: IMPLEMENT_REFCOUNTING(MediaSubmit);
};
class CredentialSubmit final : public CefV8Handler {
 public:
  bool Execute(const CefString&,CefRefPtr<CefV8Value>,const CefV8ValueList& args,
               CefRefPtr<CefV8Value>&,CefString&) override {
    if(args.size()!=2||!args[0]->IsString()||!args[1]->IsString())return true;
    auto context=CefV8Context::GetCurrentContext();if(!context||!context->GetFrame()->IsMain())return true;
    auto frame=context->GetFrame();CefURLParts parts;
    if(!CefParseURL(frame->GetURL(),parts)||(CefString(&parts.scheme)!="https"&&CefString(&parts.scheme)!="http"))return true;
    auto message=CefProcessMessage::Create("soulu.credential.submit");
    message->GetArgumentList()->SetString(0,args[0]->GetStringValue());
    message->GetArgumentList()->SetString(1,args[1]->GetStringValue());
    message->GetArgumentList()->SetString(2,frame->GetURL());
    frame->SendProcessMessage(PID_BROWSER,message);return true;
  }
 private:IMPLEMENT_REFCOUNTING(CredentialSubmit);
};
class CosmeticSubmit final : public CefV8Handler {
 public:
  bool Execute(const CefString&,CefRefPtr<CefV8Value>,const CefV8ValueList& args,
               CefRefPtr<CefV8Value>&,CefString&) override {
    if(args.size()!=1||!args[0]->IsString()||args[0]->GetStringValue().length()>65536)return true;
    auto context=CefV8Context::GetCurrentContext();if(!context)return true;
    auto message=CefProcessMessage::Create("soulu.adblock.cosmetic");
    message->GetArgumentList()->SetString(0,args[0]->GetStringValue());
    context->GetFrame()->SendProcessMessage(PID_BROWSER,message);return true;
  }
 private:IMPLEMENT_REFCOUNTING(CosmeticSubmit);
};
class RendererApp final : public CefApp, public CefRenderProcessHandler {
 public:
  CefRefPtr<CefRenderProcessHandler> GetRenderProcessHandler() override { return this; }
  void OnBrowserCreated(CefRefPtr<CefBrowser> browser,CefRefPtr<CefDictionaryValue> extra) override {
    if(extra&&extra->GetBool("souluIncognito"))private_browsers_.insert(browser->GetIdentifier());
  }
  void OnBrowserDestroyed(CefRefPtr<CefBrowser> browser) override {private_browsers_.erase(browser->GetIdentifier());}
  void OnWebKitInitialized() override {
    CefMessageRouterConfig config;
    router_ = CefMessageRouterRendererSide::Create(config);
  }
  void OnContextCreated(CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame> frame,
                        CefRefPtr<CefV8Context> context) override {
    router_->OnContextCreated(browser, frame, context);
    InstallVideoRuntime(browser,frame,context);
    CefURLParts parts;
    if(!CefParseURL(frame->GetURL(),parts)||(CefString(&parts.scheme)!="https"&&CefString(&parts.scheme)!="http"))return;
    // Isolated DevTools/translation worlds share the DOM but have independent
    // globals. Installing a second blocked play listener there pauses media even
    // after the main world is activated. Own media lifecycle in the main world.
    auto main_context=frame->GetV8Context();
    if(main_context&&main_context->IsSame(context)){
    context->GetGlobal()->SetValue("__souluMediaSend",CefV8Value::CreateFunction("media",new MediaSubmit()),V8_PROPERTY_ATTRIBUTE_NONE);
    if(frame->IsMain()&&!private_browsers_.count(browser->GetIdentifier()))
      context->GetGlobal()->SetValue("__souluFillRequest",CefV8Value::CreateFunction("fill",new MediaSubmit()),V8_PROPERTY_ATTRIBUTE_NONE);
    {CefRefPtr<CefV8Value> result;CefRefPtr<CefV8Exception> error;
      context->Eval(R"JS((()=>{
        const send=window.__souluMediaSend,fill=window.__souluFillRequest;
        delete window.__souluMediaSend;delete window.__souluFillRequest;
        let blocked=true,last=false;const pending=new Set(),play=HTMLMediaElement.prototype.play;
        // Side taps observe actual Web Audio samples without rerouting playback.
        // Analyser outputs are deliberately disconnected: audible graph is unchanged.
        const taps=new Set(),connect=AudioNode.prototype.connect,disconnect=AudioNode.prototype.disconnect;
        AudioNode.prototype.connect=function(target,output=0,input=0){
          const result=connect.apply(this,arguments);
          if(target instanceof AudioDestinationNode&&taps.size<256&&![...taps].some(t=>t.source===this&&t.target===target&&t.output===output)){
            try{const analyser=this.context.createAnalyser();analyser.fftSize=256;connect.call(this,analyser,output,0);taps.add({source:this,target,output,analyser,samples:new Float32Array(256)});}catch{}
          }return result;
        };
        AudioNode.prototype.disconnect=function(target,output){
          const result=disconnect.apply(this,arguments);
          for(const tap of taps)if(tap.source===this&&(!arguments.length||typeof target==='number'&&tap.output===target||target===tap.target&&(arguments.length<2||output===tap.output))){
            try{disconnect.call(this,tap.analyser,tap.output,0);}catch{}taps.delete(tap);
          }return result;
        };
        const webAudioActive=()=>{let active=false;for(const tap of taps){if(tap.source.context.state==='closed'){taps.delete(tap);continue;}if(tap.source.context.state!=='running')continue;
          tap.analyser.getFloatTimeDomainData(tap.samples);if(tap.samples.some(v=>Math.abs(v)>.001))active=true;
        }return active;};
        const report=()=>{const active=[...document.querySelectorAll('audio,video')].some(e=>!e.paused&&!e.ended&&!e.muted&&e.volume>0&&e.readyState>=3&&!e.seeking)||webAudioActive();if(active!==last||active){last=active;send(active);}};
        HTMLMediaElement.prototype.play=function(...args){if(blocked){pending.add(this);return Promise.reject(new DOMException('Select this tab to start playback','NotAllowedError'));}return play.apply(this,args);};
        const guard=e=>{if(blocked){pending.add(e.target);e.target.pause();}report();};
        document.addEventListener('play',guard,true);
        for(const event of ['playing','pause','ended','volumechange','emptied','waiting'])document.addEventListener(event,report,true);
        let timer=setInterval(report,500);
        Object.defineProperty(window,'__souluMediaPolicy',{configurable:true,value:defer=>{
          blocked=defer;if(!blocked){for(const element of pending)if(element.isConnected)play.call(element).catch(()=>{});pending.clear();}report();
        }});
        addEventListener('pagehide',()=>{clearInterval(timer);last=false;send(false);});
        addEventListener('pageshow',()=>{clearInterval(timer);timer=setInterval(report,500);last=false;report();});
        if(fill)document.addEventListener('pointerup',event=>{
          const e=event.target;if(!event.isTrusted||event.button!==0||!(e instanceof HTMLInputElement)||!['password','text','email'].includes(e.type))return;
          const x=Math.round(event.clientX),y=Math.round(event.clientY);setTimeout(()=>fill(x,y),0);
        },true);
      })())JS",frame->GetURL(),0,result,error);
      frame->SendProcessMessage(PID_BROWSER,CefProcessMessage::Create("soulu.media.ready"));
    }
    }
    context->GetGlobal()->SetValue("__souluCosmeticSend",CefV8Value::CreateFunction("send",new CosmeticSubmit()),V8_PROPERTY_ATTRIBUTE_NONE);
    {CefRefPtr<CefV8Value> result;CefRefPtr<CefV8Exception> error;
      context->Eval(kCosmeticBootstrap,frame->GetURL(),0,result,error);}
    if(frame->IsMain()){
      context->GetGlobal()->SetValue("__souluPageScroll",CefV8Value::CreateFunction("scroll",new PageScrollSubmit()),V8_PROPERTY_ATTRIBUTE_NONE);
      CefRefPtr<CefV8Value> result;CefRefPtr<CefV8Exception> error;
      context->Eval(kPageGlassInsetScript,frame->GetURL(),0,result,error);
      context->Eval(R"JS((()=>{const send=window.__souluPageScroll;delete window.__souluPageScroll;const raf=requestAnimationFrame.bind(window);let pending=false,y=0;
        const report=()=>{pending=false;send(y)};
        addEventListener('scroll',event=>{const node=event.target;let value=scrollY;
          if(node instanceof Element){const r=node.getBoundingClientRect();if(r.top<=64&&r.height>=innerHeight*.65)value=node.scrollTop;}
          y=Math.max(0,value);if(!pending){pending=true;raf(report)}
        },{capture:true,passive:true});addEventListener('pageshow',()=>{y=Math.max(0,scrollY);report()});
      })())JS",frame->GetURL(),0,result,error);
    }
    if(!frame->IsMain()||private_browsers_.count(browser->GetIdentifier()))return;
    context->GetGlobal()->SetValue("__souluCredentialSubmit",
      CefV8Value::CreateFunction("submit",new CredentialSubmit()),V8_PROPERTY_ATTRIBUTE_NONE);
    // The native hook is captured in a closure and removed from window. Only a
    // trusted form-submit event reads the submitted form, never all page fields.
    CefRefPtr<CefV8Value> result;CefRefPtr<CefV8Exception> error;
    context->Eval(R"JS((()=>{
      const send=window.__souluCredentialSubmit;delete window.__souluCredentialSubmit;
      document.addEventListener('submit',event=>{
        if(!event.isTrusted||event.defaultPrevented||!(event.target instanceof HTMLFormElement))return;
        const form=event.target;
        if(new URL(form.action||location.href,location.href).origin!==location.origin)return;
        const fields=[...form.elements];
        const passwords=fields.filter(el=>el instanceof HTMLInputElement&&el.type==='password'&&!el.disabled&&el.value);
        if(passwords.length!==1||passwords[0].autocomplete==='new-password')return;
        const user=fields.find(el=>el instanceof HTMLInputElement&&!el.disabled&&el.autocomplete==='username')||
          fields.find(el=>el instanceof HTMLInputElement&&!el.disabled&&(el.type==='email'||el.type==='text'));
        if(passwords[0].value.length>16384||(user&&user.value.length>4096))return;
        send(user?user.value:'',passwords[0].value);
      },true);
    })())JS",frame->GetURL(),0,result,error);
  }
  void OnContextReleased(CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame> frame,
                         CefRefPtr<CefV8Context> context) override {
    // Document pagehide and OnBeforeBrowse clear playback. Releasing an
    // isolated service world must not clear a still-playing document, and the
    // main-world context may already be gone at this point.
    ForgetVideoContext(context);
    router_->OnContextReleased(browser, frame, context);
  }
  bool OnProcessMessageReceived(CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame> frame,
                                CefProcessId source, CefRefPtr<CefProcessMessage> message) override {
    if(source==PID_BROWSER&&frame&&(message->GetName()=="soulu.media.activate"||message->GetName()=="soulu.media.policy")){
      auto context=frame->GetV8Context();if(!context)return true;
      const bool blocked=message->GetName()=="soulu.media.policy"&&message->GetArgumentList()->GetBool(0);
      context->Enter();CefRefPtr<CefV8Value> result;CefRefPtr<CefV8Exception> error;
      context->Eval(blocked?"window.__souluMediaPolicy?.(true)":"window.__souluMediaPolicy?.(false)",frame->GetURL(),0,result,error);
      context->Exit();return true;
    }
    if(HandleVideoResponse(frame,source,message))return true;
    if(source==PID_BROWSER&&frame&&(message->GetName()=="soulu.adblock.selectors"||message->GetName()=="soulu.adblock.refresh")){
      auto context=frame->GetV8Context();if(!context)return true;
      std::string script;
      if(message->GetName()=="soulu.adblock.refresh")script="window.__souluCosmetic?.refresh()";
      else {
        auto args=message->GetArgumentList();if(args->GetSize()!=2||args->GetType(1)!=VTYPE_LIST)return true;
        auto value=CefValue::Create();value->SetList(args->GetList(1)->Copy());
        // JSON serialization keeps quotes, backslashes and selectors as data.
        const std::string selectors=CefWriteJSON(value,JSON_WRITER_DEFAULT);
        script="(()=>{const s=window.__souluCosmetic;if(!s)return;";
        if(!args->GetBool(0))script+="s.sheet.replaceSync('');s.selectors.clear();";
        else script+="for(const selector of "+selectors+R"JS(){
          if(s.selectors.has(selector)||/[{};@]/.test(selector)||selector.length>4096)continue;
          try{s.sheet.insertRule(selector+'{display:none!important}',s.sheet.cssRules.length);s.selectors.add(selector);}catch(e){}
        })JS";
        script+="})()";
      }
      context->Enter();CefRefPtr<CefV8Value> result;CefRefPtr<CefV8Exception> error;
      context->Eval(script,frame->GetURL(),0,result,error);context->Exit();return true;
    }
    return router_->OnProcessMessageReceived(browser, frame, source, message);
  }
 private:
  std::set<int> private_browsers_;
  CefRefPtr<CefMessageRouterRendererSide> router_;
  IMPLEMENT_REFCOUNTING(RendererApp);
};

CefRefPtr<CefApp> CreateRendererApp() { return new RendererApp(); }
}
