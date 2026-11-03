#include "chrome/browser/ui/webui_browser/soulu_message_handler.h"

#include "base/functional/bind.h"
#include "base/strings/utf_string_conversions.h"
#include "base/task/sequenced_task_runner.h"
#include "chrome/app/chrome_command_ids.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/browser_commands.h"
#include "chrome/browser/ui/browser_window/public/browser_window_interface.h"
#include "chrome/browser/ui/webui_browser/webui_browser_window.h"
#include "components/browser_apis/tab_strip/types/node_id.h"
#include "components/prefs/pref_service.h"
#include "components/prefs/scoped_user_pref_update.h"
#include "components/tabs/public/tab_interface.h"
#include "components/url_formatter/url_fixer.h"
#include "content/public/browser/navigation_controller.h"
#include "content/public/browser/web_contents.h"
#include "content/public/browser/web_ui.h"
#include "content/public/common/referrer.h"
#include "net/base/escape.h"
#include "ui/base/page_transition_types.h"
#include "url/gurl.h"

namespace {
constexpr char kSettingsPref[] = "soulu.settings";
std::string Id(tabs::TabInterface* tab) {
  return std::string(tabs_api::NodeId::FromTabHandle(tab->GetHandle()).Id());
}
}  // namespace

SouluMessageHandler::SouluMessageHandler(BrowserWindowInterface* browser)
    : browser_(browser) {
  CHECK(browser_);
  observation_.Observe(browser_->GetTabStripModel());
}
SouluMessageHandler::~SouluMessageHandler() = default;

void SouluMessageHandler::RegisterMessages() {
  web_ui()->RegisterMessageCallback(
      "soulu.request", base::BindRepeating(&SouluMessageHandler::Request,
                                           base::Unretained(this)));
}
void SouluMessageHandler::OnJavascriptDisallowed() {
  weak_factory_.InvalidateWeakPtrs();
  state_pending_ = false;
}

base::DictValue SouluMessageHandler::Settings() const {
  auto settings = browser_->GetProfile()->GetPrefs()->GetDict(kSettingsPref).Clone();
  // The port exposes only the original adaptive layout.
  settings.Set("layout", "adaptive");
  if (!settings.FindString("theme")) settings.Set("theme", "system");
  if (!settings.FindString("language")) settings.Set("language", "ru");
  if (!settings.FindString("addressPosition")) settings.Set("addressPosition", "center");
  if (!settings.FindString("extensionsPosition")) settings.Set("extensionsPosition", "left");
  if (!settings.FindString("downloadsMode")) settings.Set("downloadsMode", "dynamic");
  if (!settings.FindString("addressOpenMode")) settings.Set("addressOpenMode", "current");
  if (!settings.FindBool("mattePanel")) settings.Set("mattePanel", false);
  return settings;
}

base::DictValue SouluMessageHandler::Snapshot() const {
  auto* model = browser_->GetTabStripModel();
  base::DictValue state;
  base::ListValue tabs;
  for (int i = 0; i < model->count(); ++i) {
    auto* contents = model->GetWebContentsAt(i);
    const auto id = Id(model->GetTabAtIndex(i));
    base::DictValue tab;
    tab.Set("id", id);
    // This is the NodeIdConverter wire format used by Chromium's tab service.
    tab.Set("guestTabId", id + ":2");
    tab.Set("title", base::UTF16ToUTF8(contents->GetTitle()));
    tab.Set("url", contents->GetVisibleURL().spec());
    tab.Set("label", contents->GetVisibleURL().spec());
    tab.Set("favicon", "");
    tab.Set("active", i == model->active_index());
    tab.Set("loading", contents->IsLoading());
    tab.Set("canGoBack", contents->GetController().CanGoBack());
    tab.Set("audible", contents->IsCurrentlyAudible());
    tab.Set("muted", contents->IsAudioMuted());
    tab.Set("pinned", model->IsTabPinned(i));
    tab.Set("incognito", browser_->GetProfile()->IsOffTheRecord());
    if (i == model->active_index()) {
      state.Set("activeTabId", id);
      state.Set("page", tab.Clone());
    }
    tabs.Append(std::move(tab));
  }
  state.Set("tabs", std::move(tabs));
  state.Set("settings", Settings());
  state.Set("sidebarVisible", sidebar_visible_);
  state.Set("bookmarks", base::ListValue());
  state.Set("homeFavoriteIds", base::ListValue());
  state.Set("profiles", base::ListValue());
  state.Set("activeProfileId", browser_->GetProfile()->GetPath().BaseName().AsUTF8Unsafe());
  state.Set("incognito", browser_->GetProfile()->IsOffTheRecord());
  // These missing integrations are deliberately explicit in the native state.
  base::DictValue capabilities;
  capabilities.Set("vpn", false);
  capabilities.Set("adblock", false);
  capabilities.Set("bookmarks", false);
  capabilities.Set("souluSettingsPage", false);
  state.Set("chromiumPortCapabilities", std::move(capabilities));
  return state;
}

int SouluMessageHandler::IndexForId(const base::Value& id) const {
  if (!id.is_string()) return -1;
  auto* model = browser_->GetTabStripModel();
  for (int i = 0; i < model->count(); ++i)
    if (Id(model->GetTabAtIndex(i)) == id.GetString()) return i;
  return -1;
}
void SouluMessageHandler::Reply(const base::Value& id, bool success,
                                 base::Value result) {
  if (IsJavascriptAllowed())
    web_ui()->CallJavascriptFunctionUnsafe("souluChromiumReply", id,
                                           base::Value(success), result);
}

void SouluMessageHandler::Request(const base::ListValue& args) {
  // The existing Webium WebUIConfig restricts this controller to the shell.
  // Recheck the actual owning WebContents before accepting privileged commands.
  if (WebUIBrowserWindow::FromWebShellWebContents(web_ui()->GetWebContents()) == nullptr)
    return;
  if (args.size() != 3 || !args[0].is_string() || !args[1].is_string()) return;
  AllowJavascript();
  const auto& id = args[0];
  const auto& action = args[1].GetString();
  const auto& payload = args[2];
  auto* model = browser_->GetTabStripModel();
  auto* active = model->GetActiveWebContents();
  auto ok = [&](base::Value result = base::Value()) {
    Reply(id, true, std::move(result));
    ScheduleState();
  };
  auto fail = [&](const char* message) { Reply(id, false, base::Value(message)); };
  if (action == "browser.state.get") { ok(base::Value(Snapshot())); return; }
  if (action == "browser.settings.get") { ok(base::Value(Settings())); return; }
  if (action == "browser.settings.set") {
    if (!payload.is_dict()) { fail("Settings must be a dictionary"); return; }
    // Until full settings sessions are ported, accept only applied shell prefs.
    for (const auto item : payload.GetDict()) {
      const auto& key = item.first;
      const auto& value = item.second;
      if ((key == "theme" && value.is_string() &&
           (value.GetString() == "light" || value.GetString() == "dark" || value.GetString() == "system")) ||
          (key == "language" && value.is_string() &&
           (value.GetString() == "ru" || value.GetString() == "en")) ||
          (key == "layout" && value.is_string() && value.GetString() == "adaptive")) continue;
      fail("This setting has not been ported"); return;
    }
    ScopedDictPrefUpdate update(browser_->GetProfile()->GetPrefs(), kSettingsPref);
    for (const auto item : payload.GetDict()) update->Set(item.first, item.second.Clone());
    ok(base::Value(Settings())); return;
  }
  if (action == "browser.newTab") {
    chrome::ExecuteCommand(browser_, IDC_NEW_TAB); ok(); return;
  }
  if (action == "browser.newIncognito") {
    chrome::NewIncognitoWindow(browser_->GetProfile()); ok(); return;
  }
  if (action == "browser.switchTab" || action == "browser.closeTab" || action == "browser.pinTab") {
    const int index = IndexForId(payload);
    if (index < 0) { fail("Unknown tab in this window"); return; }
    if (action == "browser.switchTab") model->ActivateTabAt(index);
    else if (action == "browser.pinTab") model->SetTabPinned(index, !model->IsTabPinned(index));
    else {
      // Closing the final tab can destroy this handler. Do not use it afterwards.
      Reply(id, true, base::Value());
      model->CloseWebContentsAt(index, TabCloseTypes::CLOSE_USER_GESTURE | TabCloseTypes::CLOSE_CREATE_HISTORICAL_TAB);
      return;
    }
    ok(); return;
  }
  if (action == "browser.navigate") {
    if (!active || !payload.is_string()) { fail("Missing address or active tab"); return; }
    const auto& text = payload.GetString();
    // Chromium URL fixup handles hostnames. Search is intentionally limited to
    // Google until the Soulu search-provider preference is integrated.
    const GURL supplied(text);
    if (supplied.has_scheme() && !supplied.SchemeIsHTTPOrHTTPS() && !supplied.SchemeIs("about")) {
      fail("Executable, local-file and privileged schemes are not accepted"); return;
    }
    GURL url = url_formatter::FixupURL(text, std::string());
    if (!supplied.has_scheme() && text.find('.') == std::string::npos &&
        !text.starts_with("localhost"))
      url = GURL("https://www.google.com/search?q=" + net::EscapeQueryParamValue(text, true));
    if (!url.is_valid() || (!url.SchemeIsHTTPOrHTTPS() && !url.SchemeIs("about"))) {
      fail("Only HTTP(S) and about: navigation are currently implemented"); return;
    }
    active->GetController().LoadURL(url, content::Referrer(), ui::PAGE_TRANSITION_TYPED, "");
    ok(); return;
  }
  if (action == "browser.back" && active) {
    if (active->GetController().CanGoBack()) active->GetController().GoBack();
    ok(); return;
  }
  if (action == "browser.reload" && active) {
    if (active->IsLoading()) active->Stop();
    else active->GetController().Reload(content::ReloadType::NORMAL, true);
    ok(); return;
  }
  if (action == "browser.toggleSidebar") {
    sidebar_visible_ = !sidebar_visible_; ok(); return;
  }
  if (action == "window.close" || action == "window.minimize" || action == "window.maximize") {
    auto* window = WebUIBrowserWindow::FromBrowser(browser_);
    if (!window) { fail("No browser window"); return; }
    Reply(id, true, base::Value());
    if (action == "window.close") window->Close();
    else if (action == "window.minimize") window->Minimize();
    else if (window->IsMaximized()) window->Restore();
    else window->Maximize();
    return;
  }
  if (action == "browser.setSuggestionsHeight" || action == "browser.popover" ||
      action == "window.captionBounds") {
    // Chromium owns content geometry. These CEF-only sizing hints have no effect.
    Reply(id, true, base::Value()); return;
  }
  fail("Action is not yet implemented in the Chromium port");
}

void SouluMessageHandler::OnTabStripModelChanged(
    TabStripModel*, const TabStripModelChange&, const TabStripSelectionChange&) {
  ScheduleState();
}
void SouluMessageHandler::OnTabChangedAt(tabs::TabInterface*, TabChangeType) {
  ScheduleState();
}
void SouluMessageHandler::ScheduleState() {
  if (state_pending_ || !IsJavascriptAllowed()) return;
  state_pending_ = true;
  base::SequencedTaskRunner::GetCurrentDefault()->PostTask(
      FROM_HERE, base::BindOnce(&SouluMessageHandler::SendState,
                                weak_factory_.GetWeakPtr()));
}
void SouluMessageHandler::SendState() {
  state_pending_ = false;
  if (IsJavascriptAllowed())
    web_ui()->CallJavascriptFunctionUnsafe("souluChromiumState", base::Value(Snapshot()));
}
