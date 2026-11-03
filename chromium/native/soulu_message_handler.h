// Soulu Chromium port. Only installed in the browser's trusted WebUI shell.
#ifndef CHROME_BROWSER_UI_WEBUI_BROWSER_SOULU_MESSAGE_HANDLER_H_
#define CHROME_BROWSER_UI_WEBUI_BROWSER_SOULU_MESSAGE_HANDLER_H_

#include "base/memory/raw_ptr.h"
#include "base/memory/weak_ptr.h"
#include "base/scoped_observation.h"
#include "base/values.h"
#include "chrome/browser/ui/tabs/tab_strip_model.h"
#include "chrome/browser/ui/tabs/tab_strip_model_observer.h"
#include "content/public/browser/web_ui_message_handler.h"

class BrowserWindowInterface;
class SouluMessageHandler : public content::WebUIMessageHandler,
                            public TabStripModelObserver {
 public:
  explicit SouluMessageHandler(BrowserWindowInterface* browser);
  ~SouluMessageHandler() override;
  void RegisterMessages() override;
  void OnJavascriptDisallowed() override;
  void OnTabStripModelChanged(TabStripModel*, const TabStripModelChange&,
                              const TabStripSelectionChange&) override;
  void OnTabChangedAt(tabs::TabInterface*, TabChangeType) override;

 private:
  void Request(const base::ListValue& args);
  base::DictValue Snapshot() const;
  base::DictValue Settings() const;
  void ScheduleState();
  void SendState();
  void Reply(const base::Value& id, bool success, base::Value result);
  int IndexForId(const base::Value& id) const;

  raw_ptr<BrowserWindowInterface> browser_;
  base::ScopedObservation<TabStripModel, TabStripModelObserver> observation_{this};
  bool state_pending_ = false;
  bool sidebar_visible_ = false;
  base::WeakPtrFactory<SouluMessageHandler> weak_factory_{this};
};
#endif
