#pragma once
#include "examples/soulu/profile_data.h"
#include <atomic>
#include <memory>

namespace soulu {
struct ImportSource {
  std::string id, browser, name, family;
  std::filesystem::path root;
};
struct ImportControl {
  std::atomic<bool> cancelled{false};
  std::atomic<int> processed{0};
};
std::vector<ImportSource> BrowserImportSources();
CefRefPtr<CefListValue> BrowserImportCatalog();
ImportSource PortableImportSource(const std::filesystem::path&);
std::string ReadImportFile(const std::filesystem::path&);
CefRefPtr<CefDictionaryValue> BrowserImportCapabilities(const ImportSource&);
CefRefPtr<CefDictionaryValue> ImportBrowserPasswords(const ImportSource&,const std::string&,const std::shared_ptr<ImportControl>&);
CefRefPtr<CefDictionaryValue> ImportBrowserAutofill(const ImportSource&,const std::string&,const std::shared_ptr<ImportControl>&);
CefRefPtr<CefListValue> ReadImportTabs(const ImportSource&,const std::shared_ptr<ImportControl>&,CefRefPtr<CefDictionaryValue> report=nullptr);
// Readers return normalized trees/visits; they never write Soulu or source data.
CefRefPtr<CefListValue> ReadImportBookmarks(const ImportSource&, const std::shared_ptr<ImportControl>&);
CefRefPtr<CefDictionaryValue> ImportBrowserHistory(const ImportSource&, const std::string&, const std::shared_ptr<ImportControl>&);
CefRefPtr<CefDictionaryValue> ImportPasswordCsv(const std::filesystem::path&, const std::string&, const std::shared_ptr<ImportControl>&);
CefRefPtr<CefListValue> MergeImportBookmarks(CefRefPtr<CefListValue> existing, CefRefPtr<CefListValue> nodes,
    const std::string& target, CefRefPtr<CefDictionaryValue> report, const std::shared_ptr<ImportControl>&);
}
