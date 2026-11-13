"""Keep Sona's section layout; expose only controls backed by Gecko."""
import pathlib

def adapt(path):
 s=path.read_text(encoding='utf-8')
 anchor="sections.splice(0,sections.length,old.general,old.interface,old.tabs,old.search,old.sites,old.vpn,reading,translation,extensions,performance,old.profiles,old.updates);"
 extra="""
  // Preview 1 keeps the canonical section structure without pretending CEF services exist.
  const implemented=new Set(['language','defaultBrowser','downloadPath','chooseFolder','askDownloadLocation','openFolder','theme','mattePanel','layout','showSidebar','showBack','showHome','showFavorites','showNewTab','showDownloads','vpnToolbarVisible','addressPosition','bookmarksBarMode','bookmarksIconsOnly','openStartPageAfterLastTab','startupMode','startupUrl','newTabMode','newTabUrl','homeMode','homeUrl','searchEngine','geolocation','camera','microphone','notifications','popups','contentBlocking','exceptions','history','clearData','passwords','siteData','profiles','directDomains','versions','vpnComponents','profileList','createProfile','incognito','import','performanceMode']);
  for(const section of sections)for(const group of section.groups)group.rows=group.rows.filter(r=>implemented.has(r.key));
  for(const section of sections)section.groups=section.groups.filter(g=>g.rows.length);
  old.sites.groups.push(group('Настройки сайта','Site controls',[action('geckoSiteSettings','Разрешения и исключения Firefox','Firefox permissions and exceptions'),action('geckoAdblockSettings','Настройки uBlock Origin','uBlock Origin settings')]));
  reading.groups=[group('Режим чтения Gecko','Gecko reader',[action('geckoReader','Открыть режим чтения текущей страницы','Open reader for the current page')])];
  translation.groups=[group('Перевод Firefox','Firefox translation',[action('geckoTranslation','Настройки перевода Firefox','Firefox translation settings')])];
  extensions.groups=[group('Расширения Firefox','Firefox extensions',[action('geckoExtensions','Управление расширениями','Manage extensions'),action('geckoExtensionStore','Открыть каталог Firefox','Open Firefox add-ons')])];
"""
 assert anchor in s;s=s.replace(anchor,anchor+extra)
 s=s.replace("async function runAction(key){", "async function runAction(key){if(key.startsWith('gecko'))return invoke(key);")
 path.write_text(s,encoding='utf-8')
