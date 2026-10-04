//! Narrow C ABI: filter text is data; no scriptlets or downloaded code execution.
use adblock::{Engine, lists::{FilterSet, ParseOptions}, request::Request};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{ffi::{CStr, CString, c_char}, fs, io::Read, path::{Path, PathBuf},
    sync::{Arc, OnceLock, RwLock}, time::{Duration, SystemTime, UNIX_EPOCH}};

const SOURCES: [&str; 3] = ["https://easylist.to/easylist/easylist.txt",
    "https://easylist.to/easylist/easyprivacy.txt",
    "https://easylist-downloads.adblockplus.org/ruadlist.txt"];
const BASELINE: [&str; 3] = [include_str!("../filters/easylist.txt"),
    include_str!("../filters/easyprivacy.txt"), include_str!("../filters/ruadlist.txt")];
const INTERVAL: u64 = 24 * 60 * 60;
const LIMIT: usize = 16 * 1024 * 1024;
static STATE: OnceLock<RwLock<State>> = OnceLock::new();

#[derive(Clone, Serialize, Deserialize)]
struct Bundle { schema: u32, updated: u64, lists: Vec<String>, digest: String }
struct Rules { engine: Engine, network: u64, cosmetic: u64, versions: Vec<String> }
struct State { rules: Arc<Rules>, updated: u64, error: String, origin: String }
fn now() -> u64 { SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs() }
fn digest(lists: &[String]) -> String {
    let mut hash = Sha256::new();
    for text in lists { hash.update((text.len() as u64).to_le_bytes()); hash.update(text); }
    format!("{:x}", hash.finalize())
}
fn compile(lists: &[String]) -> Result<Rules, String> {
    if lists.len() != 3 { return Err("Expected three filter subscriptions".into()); }
    let mut set = FilterSet::new(true);
    let mut versions = Vec::new();
    for (i, text) in lists.iter().enumerate() {
        if text.len() < 10000 || text.len() > LIMIT || text.contains('\0') ||
            !text.trim_start_matches('\u{feff}').starts_with("[Adblock Plus") ||
            text.to_ascii_lowercase().contains("<!doctype html") {
            return Err(format!("Invalid filter content: {}", SOURCES[i]));
        }
        let version = text.lines().take(40).find_map(|s| s.strip_prefix("! Version: "))
            .ok_or("Filter version missing")?;
        if version.len() > 64 { return Err("Invalid version".into()); }
        versions.push(version.to_owned());
        set.add_filter_list(text.clone(), ParseOptions::default());
    }
    let engine = Engine::new_with_filter_set(set);
    let info = engine.get_debug_info();
    if info.source_info.len() != 3 || info.source_info.iter().any(|s| s.network_filter_count < 1000) {
        return Err("Insufficient parsed network rules".into());
    }
    let network = info.source_info.iter().map(|s| s.network_filter_count as u64).sum();
    let cosmetic = info.source_info.iter().map(|s| s.cosmetic_filter_count as u64).sum();
    if cosmetic < 1000 { return Err("Insufficient cosmetic rules".into()); }
    Ok(Rules {engine, network, cosmetic, versions})
}
fn baseline() -> Vec<String> { BASELINE.iter().map(|s| s.to_string()).collect() }
fn read_cache(path: &Path) -> Result<(Rules, u64), String> {
    let bytes = fs::read(path).map_err(|e| e.to_string())?;
    if bytes.len() > LIMIT * 4 { return Err("Oversize cache".into()); }
    let bundle: Bundle = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
    if bundle.schema != 1 || bundle.digest != digest(&bundle.lists) || bundle.updated > now() + 300 {
        return Err("Corrupt filter cache".into());
    }
    Ok((compile(&bundle.lists)?, bundle.updated))
}
fn save_cache(path: &Path, bundle: &Bundle) -> Result<(), String> {
    let parent = path.parent().ok_or("Invalid cache path")?;
    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    let temp = path.with_extension("pending");
    let mut file = fs::File::create(&temp).map_err(|e| e.to_string())?;
    serde_json::to_writer(&mut file, bundle).map_err(|e| e.to_string())?;
    file.sync_all().map_err(|e| e.to_string())?;
    drop(file);
    atomic_replace(&temp, path)
}
#[cfg(windows)]
fn atomic_replace(from: &Path, to: &Path) -> Result<(), String> {
    use std::os::windows::ffi::OsStrExt;
    unsafe extern "system" { fn MoveFileExW(from: *const u16, to: *const u16, flags: u32) -> i32; }
    let from: Vec<u16> = from.as_os_str().encode_wide().chain(Some(0)).collect();
    let to: Vec<u16> = to.as_os_str().encode_wide().chain(Some(0)).collect();
    if unsafe { MoveFileExW(from.as_ptr(), to.as_ptr(), 1 | 8) } == 0 {
        Err(std::io::Error::last_os_error().to_string())
    } else { Ok(()) }
}
#[cfg(not(windows))]
fn atomic_replace(from: &Path, to: &Path) -> Result<(), String> { fs::rename(from,to).map_err(|e|e.to_string()) }
fn update(path: &Path) -> Result<(), String> {
    let client = reqwest::blocking::Client::builder().timeout(Duration::from_secs(30))
        .connect_timeout(Duration::from_secs(10)).https_only(true)
        .redirect(reqwest::redirect::Policy::none()).build().map_err(|e| e.to_string())?;
    let mut lists = Vec::new();
    for source in SOURCES {
        let response = client.get(source).send().map_err(|e| e.to_string())?
            .error_for_status().map_err(|e| e.to_string())?;
        if !response.status().is_success() { return Err("Filter redirect rejected".into()); }
        let kind = response.headers().get(reqwest::header::CONTENT_TYPE)
            .and_then(|s| s.to_str().ok()).unwrap_or("");
        if !kind.starts_with("text/plain") { return Err("Invalid filter content type".into()); }
        let mut bytes = Vec::new();
        response.take((LIMIT + 1) as u64).read_to_end(&mut bytes).map_err(|e|e.to_string())?;
        if bytes.len() > LIMIT { return Err("Oversize filter download".into()); }
        lists.push(String::from_utf8(bytes).map_err(|e|e.to_string())?);
    }
    let rules = compile(&lists)?;
    let state = STATE.get().ok_or("Engine not initialized")?;
    {
        let old = state.read().map_err(|_|"State unavailable")?;
        if rules.network < old.rules.network / 2 || rules.cosmetic < old.rules.cosmetic / 2 {
            return Err("Suspicious filter count reduction".into());
        }
    }
    let bundle = Bundle {schema:1, updated:now(), digest:digest(&lists), lists};
    save_cache(path, &bundle)?;
    let mut state = state.write().map_err(|_|"State unavailable")?;
    state.rules = Arc::new(rules); state.updated = bundle.updated;
    state.error.clear(); state.origin = "cache".into();
    Ok(())
}
fn rules() -> Option<Arc<Rules>> { STATE.get()?.read().ok().map(|s| Arc::clone(&s.rules)) }
// Every ABI entry contains panic propagation; no Rust panic may unwind into C++.
fn boundary<T: Default>(f: impl FnOnce() -> T) -> T {
    std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)).unwrap_or_default()
}
unsafe fn input<'a>(ptr: *const c_char) -> &'a str {
    if ptr.is_null() { "" } else { unsafe { CStr::from_ptr(ptr) }.to_str().unwrap_or("") }
}
fn output(text: String) -> *mut c_char { CString::new(text).map(CString::into_raw).unwrap_or(std::ptr::null_mut()) }
#[unsafe(no_mangle)]
pub unsafe extern "C" fn soulu_ab_init(cache: *const c_char, fixture: *const c_char, updates: bool) -> bool { boundary(|| {
    let path = PathBuf::from(unsafe {input(cache)});
    let (rules, updated, error, origin) = match read_cache(&path) {
        Ok((r,u)) => (r,u,String::new(),"cache"),
        Err(e) => { let Ok(r) = compile(&baseline()) else { return false; };
            (r,0,if path.exists(){e}else{String::new()},"bundled") }
    };
    let fixture=unsafe {input(fixture)};
    let rules=if fixture.is_empty(){rules}else{
        let Ok(text)=fs::read_to_string(fixture) else{return false;};
        if text.len()>65536{return false;}
        let mut set=FilterSet::new(true);
        for list in baseline(){set.add_filter_list(list,ParseOptions::default());}
        set.add_filter_list(text,ParseOptions::default());
        Rules{engine:Engine::new_with_filter_set(set),..rules}
    };
    if STATE.set(RwLock::new(State {rules:Arc::new(rules),updated,error,origin:origin.into()})).is_err() { return false; }
    if updates {std::thread::spawn(move || loop {
        let due = STATE.get().and_then(|s|s.read().ok()).map(|s| now().saturating_sub(s.updated)>=INTERVAL).unwrap_or(false);
        if due { if let Err(e) = std::panic::catch_unwind(std::panic::AssertUnwindSafe(||update(&path))).unwrap_or_else(|_|Err("Filter update panic; retained working rules".into())) {
            if let Some(state) = STATE.get() { if let Ok(mut s) = state.write() {s.error=e;} }
        } }
        std::thread::sleep(Duration::from_secs(3600));
    });}
    true
}) }
#[unsafe(no_mangle)]
pub unsafe extern "C" fn soulu_ab_check(url: *const c_char, source: *const c_char,
    kind: *const c_char, method: *const c_char) -> *mut c_char { boundary(|| {
    let Some(rules) = rules() else {return output("{\"ready\":false}".into());};
    let request = Request::new(unsafe {input(url)},unsafe {input(source)},unsafe {input(kind)},unsafe {input(method)});
    let Ok(request) = request else {return output("{\"matched\":false}".into());};
    let result = rules.engine.check_network_request(&request);
    output(serde_json::json!({"ready":true,"matched":result.matched,
        "rule":result.filter,"exception":result.exception}).to_string())
}) }
#[derive(Default, Deserialize)]
struct Tokens { #[serde(default)] classes:Vec<String>, #[serde(default)] ids:Vec<String> }
#[unsafe(no_mangle)]
pub unsafe extern "C" fn soulu_ab_cosmetic(url: *const c_char, tokens: *const c_char) -> *mut c_char { boundary(|| {
    let Some(rules) = rules() else {return output("[]".into());};
    let tokens: Tokens = serde_json::from_str(unsafe {input(tokens)}).unwrap_or_default();
    let resources = rules.engine.url_cosmetic_resources(unsafe {input(url)});
    let mut selectors = resources.hide_selectors;
    if !resources.generichide {
        selectors.extend(rules.engine.hidden_class_id_selectors(tokens.classes.iter().take(256),
            tokens.ids.iter().take(256), &resources.exceptions));
    }
    output(serde_json::to_string(&selectors).unwrap_or_else(|_|"[]".into()))
}) }
#[unsafe(no_mangle)]
pub extern "C" fn soulu_ab_status() -> *mut c_char { boundary(|| {
    let Some(state) = STATE.get().and_then(|s|s.read().ok()) else {return output("{\"ready\":false}".into());};
    output(serde_json::json!({"ready":true,"engine":"adblock-rust 0.13.3",
        "networkRules":state.rules.network,"cosmeticRules":state.rules.cosmetic,
        "versions":state.rules.versions,"lastSuccessfulUpdate":state.updated,
        "lastUpdateError":state.error,"source":state.origin,"updateIntervalSeconds":INTERVAL}).to_string())
}) }
#[unsafe(no_mangle)]
pub unsafe extern "C" fn soulu_ab_free(ptr: *mut c_char) {
    if !ptr.is_null() { drop(unsafe {CString::from_raw(ptr)}); }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn engine(text: &str) -> Engine { let mut set=FilterSet::new(true);
        set.add_filter_list(text.to_owned(),ParseOptions::default());Engine::new_with_filter_set(set) }
    fn blocked(e:&Engine,url:&str,source:&str,kind:&str)->bool {
        e.check_network_request(&Request::new(url,source,kind,"get").unwrap()).matched }
    #[test] fn network_context_and_exceptions() {
        let e=engine("||ads.example.net^$third-party,script,image,subdocument,xmlhttprequest\n@@||ads.example.net/allowed.js$script\n||cdn.example.co.uk^$third-party\n||metrics.example.net^$domain=news.example.org\n|https://exact.example/a|\n/banner/*/ad^$image\n||first.example^$~third-party");
        for kind in ["script","image","subdocument","xmlhttprequest"] {
            assert!(blocked(&e,"https://ADS.example.net/ad", "https://news.example.org",kind)); }
        assert!(!blocked(&e,"https://ads.example.net/allowed.js","https://news.example.org","script"));
        assert!(!blocked(&e,"https://ads.example.net/ad","https://news.example.org","font"));
        assert!(!blocked(&e,"https://cdn.example.co.uk/ad","https://www.example.co.uk","script"));
        assert!(blocked(&e,"https://cdn.example.co.uk/ad","https://different.co.uk","script"));
        assert!(blocked(&e,"https://metrics.example.net/a","https://news.example.org","xmlhttprequest"));
        assert!(!blocked(&e,"https://metrics.example.net/a","https://other.org","xmlhttprequest"));
        assert!(blocked(&e,"https://exact.example/a","https://other.org","image"));
        assert!(!blocked(&e,"https://exact.example/ab","https://other.org","image"));
        assert!(blocked(&e,"https://host.example/banner/test/ad.gif","https://other.org","image"));
        assert!(blocked(&e,"https://cdn.first.example/a","https://first.example","script"));
    }
    #[test] fn cosmetic_selection() {
        let e=engine("##.advert\nnews.example##.banner\nnews.example#@#.advert");
        let r=e.url_cosmetic_resources("https://news.example");
        assert!(r.hide_selectors.contains(".banner"));
        assert!(e.hidden_class_id_selectors(["advert"],Vec::<String>::new(),&r.exceptions).is_empty());
        let r=e.url_cosmetic_resources("https://other.example");
        assert!(e.hidden_class_id_selectors(["advert"],Vec::<String>::new(),&r.exceptions).contains(&".advert".into()));
        assert!(!r.hide_selectors.contains(".banner"));
    }
    #[test] fn baseline_and_cache_recovery() {
        let lists=baseline(); let r=compile(&lists).unwrap(); assert!(r.network>10000&&r.cosmetic>10000);
        let root=std::env::temp_dir().join(format!("soulu-filter-test-{}",std::process::id()));
        fs::create_dir_all(&root).unwrap();let path=root.join("cache.json");
        let b=Bundle{schema:1,updated:now(),digest:digest(&lists),lists};
        save_cache(&path,&b).unwrap();assert!(read_cache(&path).is_ok());
        fs::write(&path,"<html>Error</html>").unwrap();assert!(read_cache(&path).is_err());
        assert!(compile(&baseline()).is_ok());fs::remove_dir_all(root).unwrap();
    }
    #[test] fn invalid_update_keeps_last_known_good() {
        let lists=baseline();assert!(compile(&vec!["<html>error</html>".into();3]).is_err());
        let old=compile(&lists).unwrap();let e=&old.engine;
        assert!(blocked(e,"https://ad.doubleclick.net/ad.js","https://example.org","script"));
    }
}
