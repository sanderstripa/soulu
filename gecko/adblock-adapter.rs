// Gecko owns network downloads so proxy, DNS, TLS and fail-closed policy stay native.
// Only compilation and atomic cache installation run in this worker.
static GECKO_UPDATING: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
#[unsafe(no_mangle)]
pub unsafe extern "C" fn sona_ab_install_files(directory: *const c_char, cache: *const c_char) -> bool { boundary(|| {
    use std::sync::atomic::Ordering;
    if directory.is_null() || cache.is_null() {return false;}
    let directory=PathBuf::from(unsafe{CStr::from_ptr(directory)}.to_string_lossy().into_owned());
    let cache=PathBuf::from(unsafe{CStr::from_ptr(cache)}.to_string_lossy().into_owned());
    if GECKO_UPDATING.swap(true,Ordering::SeqCst){return false;}
    std::thread::spawn(move||{
        let result=std::panic::catch_unwind(||->Result<(),String>{
            let mut lists=Vec::new();
            for i in 0..3 {let p=directory.join(format!("{i}.txt"));if fs::metadata(&p).map_err(|e|e.to_string())?.len()>LIMIT as u64{return Err("Oversize filters".into());}lists.push(fs::read_to_string(p).map_err(|e|e.to_string())?);}
            install_update(&cache,lists,STATE.get().ok_or("Engine unavailable")?)
        }).unwrap_or_else(|_|Err("Filter worker failed".into()));
        if let Err(error)=result{if let Some(state)=STATE.get(){if let Ok(mut s)=state.write(){s.error=error;}}}
        let _=fs::remove_dir_all(directory);GECKO_UPDATING.store(false,Ordering::SeqCst);
    });true
}) }
#[unsafe(no_mangle)]
pub extern "C" fn sona_ab_updating() -> bool {GECKO_UPDATING.load(std::sync::atomic::Ordering::SeqCst)}
