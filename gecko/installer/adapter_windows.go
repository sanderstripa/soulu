//go:build windows

package sona

import (
	"archive/zip"
	"bytes"
	"connect-installer.local/core/core"
	"connect-installer.local/core/products"
	"crypto/sha256"
	"embed"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"golang.org/x/sys/windows/registry"
 "golang.org/x/sys/windows"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
 "strconv"
 "syscall"
	"sync/atomic"
)

//go:embed payload.zip ribbon.png
var assets embed.FS

const uninstallKey = `Software\Microsoft\Windows\CurrentVersion\Uninstall\Sona`

// Remove only our uninstaller and empty application directories after exit.
// The shared installer core does not recognize the Gecko uninstaller name.
func (a *Adapter) AfterRemoval() error {
 target,err:=core.OwnedPath(a.dir,"Uninstall Sona.exe");if err!=nil{return err}
 script:=`Wait-Process -Id `+strconv.Itoa(os.Getpid())+` -ErrorAction SilentlyContinue;Start-Sleep -Milliseconds 300;$root=`+core.QuotePS(a.dir)+`;Remove-Item -LiteralPath `+core.QuotePS(target)+` -Force -ErrorAction SilentlyContinue;Get-ChildItem -LiteralPath $root -Directory -Recurse -Force -ErrorAction SilentlyContinue|Sort-Object { $_.FullName.Length } -Descending|ForEach-Object {if(@(Get-ChildItem -LiteralPath $_.FullName -Force).Count -eq 0){Remove-Item -LiteralPath $_.FullName}};if((Test-Path -LiteralPath $root) -and @(Get-ChildItem -LiteralPath $root -Force).Count -eq 0){Remove-Item -LiteralPath $root};`
 cmd:=exec.Command("powershell.exe","-NoProfile","-NonInteractive","-Command",script);cmd.SysProcAttr=&syscall.SysProcAttr{HideWindow:true};return cmd.Start()
}

type Adapter struct {
	dir       string
	progress  atomic.Int32
	installed bool
}

func New() *Adapter {
	dir := filepath.Join(os.Getenv("LOCALAPPDATA"), "Programs", "Sona")
	if k, e := registry.OpenKey(registry.CURRENT_USER, `Software\Sona`, registry.QUERY_VALUE); e == nil {
		if p, _, e := k.GetStringValue("InstallDir"); e == nil {
			dir = p
		}
		k.Close()
	}
	return &Adapter{dir: dir}
}
func (a *Adapter) Config() core.Config {
	return products.Configure("sona", a.dir, assets)
}
func (a *Adapter) Progress() core.Progress            { return core.Progress{Percent: int(a.progress.Load())} }
func (a *Adapter) Action(string, []byte) (any, error) { return nil, fmt.Errorf("unknown action") }
func (a *Adapter) Open() error {
	if !a.installed {
		return fmt.Errorf("installation not complete")
	}
	return exec.Command(filepath.Join(a.dir, "Sona.exe")).Start()
}
func setReg(path string, values map[string]string) error {
	k, _, err := registry.CreateKey(registry.CURRENT_USER, path, registry.SET_VALUE)
	if err != nil {
		return err
	}
	defer k.Close()
	for n, v := range values {
		if err = k.SetStringValue(n, v); err != nil {
			return err
		}
	}
	return nil
}

// Validate the embedded Gecko payload before touching the destination.
func verifyGecko(raw []byte) error {
 zr,err:=zip.NewReader(bytes.NewReader(raw),int64(len(raw)));if err!=nil{return err}
 entries:=map[string]*zip.File{};for _,f:=range zr.File{if _,ok:=entries[f.Name];ok{return fmt.Errorf("duplicate archive entry")};entries[f.Name]=f}
 manifest:=entries["sona-engine-manifest.json"];if manifest==nil{return fmt.Errorf("Gecko integrity manifest missing")}
 r,err:=manifest.Open();if err!=nil{return err};var m struct{Name string `json:"name"`; Files []struct{Path string `json:"path"`;SHA string `json:"sha256"`} `json:"files"`};err=json.NewDecoder(io.LimitReader(r,4<<20)).Decode(&m);r.Close();if err!=nil{return err}
 if m.Name!="Sona Preview 1.160.31"||len(m.Files)<10{return fmt.Errorf("unexpected Gecko payload")}
 checked:=map[string]bool{}
 for _,item:=range m.Files{if len(item.SHA)!=64||checked[item.Path]{return fmt.Errorf("invalid manifest entry")};f:=entries[item.Path];if f==nil||f.FileInfo().IsDir(){return fmt.Errorf("missing Gecko component: %s",item.Path)};r,e:=f.Open();if e!=nil{return e};h:=sha256.New();_,e=io.Copy(h,r);r.Close();if e!=nil{return e};if !strings.EqualFold(hex.EncodeToString(h.Sum(nil)),item.SHA){return fmt.Errorf("Gecko component hash mismatch: %s",item.Path)};checked[item.Path]=true}
 for name,f:=range entries{if !f.FileInfo().IsDir()&&name!="sona-engine-manifest.json"&&!checked[name]{return fmt.Errorf("unverified file: %s",name)}}
 for _,name:=range []string{"Sona.exe","engine/SonaEngine.exe","engine/xul.dll","engine/sona.cfg","BUILD.json"}{if !checked[name]{return fmt.Errorf("required Gecko component missing: %s",name)}}
 return nil
}
// An interrupted install can lose Sona.exe. Ownership comes from the product
// manifest/build identity, not from the presence of one launcher executable.
func repairableDirectory(dir string) bool {
 if data,e:=os.ReadFile(filepath.Join(dir,core.ManifestName));e==nil{var m core.FileManifest;if json.Unmarshal(data,&m)==nil&&m.Product=="sona"{return true}}
 if data,e:=os.ReadFile(filepath.Join(dir,"BUILD.json"));e==nil{var b struct{Name string `json:"name"`;Channel string `json:"channel"`};if json.Unmarshal(data,&b)==nil&&b.Channel=="gecko-preview"&&strings.HasPrefix(b.Name,"Sona "){return true}}
 // Older uninstallers leave empty engine folders and their own executable.
 // Ignore these leftovers, while rejecting unrelated files and all links.
 clean:=true
 err:=filepath.WalkDir(dir,func(path string,item os.DirEntry,e error)error{if e!=nil{return e};if item.Type()&os.ModeSymlink!=0{clean=false;return nil};if !item.IsDir()&&path!=filepath.Join(dir,"Uninstall Sona.exe"){clean=false};return nil})
 return err==nil&&clean
}
func (a *Adapter) Install(o core.Options) error {
 if err:=checkPreviousClosed();err!=nil{return err}
 for _,oldDir:=range previousInstallations(){if previousOwned(oldDir)&&strings.EqualFold(oldDir,o.Path){return fmt.Errorf("choose the new Sona folder")}}
	a.progress.Store(0)
	dir, err := core.ValidateDir(o.Path)
	if err != nil {
		return err
	}
	profile := strings.ToLower(filepath.Join(os.Getenv("LOCALAPPDATA"), "Sona"))
	d := strings.ToLower(dir)
	if d == profile || strings.HasPrefix(d, profile+string(os.PathSeparator)) {
		return fmt.Errorf("the browser profile cannot be used as an installation folder")
	}
	if _, e := os.Stat(filepath.Join(a.dir, "Sona.exe")); e == nil && !strings.EqualFold(dir, a.dir) {
		return fmt.Errorf("update the existing installation at %s", a.dir)
	}
	if entries, e := os.ReadDir(dir); e == nil && len(entries) > 0 {
		if _, e := os.Stat(filepath.Join(dir, "Sona.exe")); e != nil && !repairableDirectory(dir) {
			return fmt.Errorf("В выбранной папке есть посторонние файлы. Выберите отдельную папку для Sona.")
		}
	}
 // Portable and installed Gecko share profiles: refuse upgrades while either owns one.
 profiles:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Sona","Profiles");if dirs,e:=os.ReadDir(profiles);e==nil{for _,entry:=range dirs{if !entry.IsDir(){continue};lock:=filepath.Join(profiles,entry.Name(),"parent.lock");if _,e=os.Stat(lock);os.IsNotExist(e){continue};name,e:=windows.UTF16PtrFromString(lock);if e!=nil{return e};handle,e:=windows.CreateFile(name,windows.GENERIC_READ,0,nil,windows.OPEN_EXISTING,windows.FILE_ATTRIBUTE_NORMAL,0);if e!=nil{return fmt.Errorf("close Sona before installing: %w",e)};windows.CloseHandle(handle)}}
 // A CEF installation is a different product, even though both use Sona.exe.
 if _,e:=os.Stat(filepath.Join(dir,"Sona.exe"));e==nil{data,e:=os.ReadFile(filepath.Join(dir,"BUILD.json"));if e!=nil{return fmt.Errorf("choose a separate Sona installation folder")};var build struct{Name string `json:"name"`;Channel string `json:"channel"`};if json.Unmarshal(data,&build)!=nil||(build.Channel!="gecko-preview"||!strings.HasPrefix(build.Name,"Sona ")){return fmt.Errorf("this folder belongs to another browser")}}
 geckoProfile:=strings.ToLower(filepath.Join(os.Getenv("LOCALAPPDATA"),"Sona"));if d==geckoProfile||strings.HasPrefix(d,geckoProfile+string(os.PathSeparator)){return fmt.Errorf("profile data cannot be used as an installation folder")}
	// Refuse a running browser. Never invoke taskkill; the user closes it normally.
	if err = core.CheckClosed(filepath.Join(dir, "engine", "SonaEngine.exe"));err!=nil{return err}
	if err = core.CheckClosed(filepath.Join(dir, "Sona.exe")); err != nil {
		return err
	}
 legacyDir:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Programs","Soul");for _,relative:=range []string{"Soul.exe",filepath.Join("engine","SoulEngine.exe")}{if err=core.CheckClosed(filepath.Join(legacyDir,relative));err!=nil{return err}}
	raw, err := assets.ReadFile("payload.zip")
	if err != nil {
		return err
	}
	if err = verifyGecko(raw); err != nil {
		return err
	}
	if err=migrateProductData(os.Getenv("LOCALAPPDATA"));err!=nil{return err}
 a.progress.Store(15)
	if err = core.Unpack(raw, dir, "sona", "Sona.exe", func(p int) { a.progress.Store(int32(p)) }); err != nil {
		return err
	}
	self, err := os.Executable()
	if err != nil {
		return err
	}
	data, err := os.ReadFile(self)
	if err != nil {
		return err
	}
	if _, err = core.OwnedPath(dir, "Uninstall Sona.exe"); err != nil {
		return err
	}
	if err = core.AtomicWrite(filepath.Join(dir, "Uninstall Sona.exe"), data); err != nil {
		return err
	}
	if err = setReg(`Software\Sona`, map[string]string{"InstallDir": dir}); err != nil {
		return err
	}
	exe := filepath.Join(dir, "Sona.exe")
	icon := filepath.Join(dir,"engine","sona","chrome","ui","sona-app-1.160.31.ico")
 cleanupLinks := `$shell=New-Object -ComObject WScript.Shell
$roots=@([Environment]::GetFolderPath('Programs'),[Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('CommonPrograms'))
$ownedRoots=@($env:SONA_LINK_ROOT,(Join-Path $env:LOCALAPPDATA 'Programs\Sona'),(Join-Path $env:LOCALAPPDATA 'Programs\Soul'),(Join-Path $env:LOCALAPPDATA 'Programs\SonaGecko'))
foreach($root in $roots){
 foreach($item in (Get-ChildItem -LiteralPath $root -Filter *.lnk -File -Recurse -ErrorAction SilentlyContinue)){
  $link=$shell.CreateShortcut($item.FullName)
  if(!$link.TargetPath -and $item.BaseName -match 'private|\u043f\u0440\u0438\u0432\u0430\u0442'){
   # WSH can return an empty target for a localized shortcut filename.
   $copy=Join-Path ([IO.Path]::GetTempPath()) (([guid]::NewGuid().ToString('N'))+'.lnk')
   try{[IO.File]::Copy($item.FullName,$copy);$link=$shell.CreateShortcut($copy)}finally{[IO.File]::Delete($copy)}
  }
  $target=[Environment]::ExpandEnvironmentVariables([string]$link.TargetPath)
  $privateEngine='(?i)(?:^|[\\/])(?:Soul|Sona|SonaGecko)[\\/]engine[\\/]private_browsing\.exe$'
  $legacy=$target.StartsWith((Join-Path $env:LOCALAPPDATA 'Programs\Soul\'),[StringComparison]::OrdinalIgnoreCase)
  $owned=$ownedRoots | Where-Object {$_ -and $target.StartsWith(($_.TrimEnd('\')+'\'),[StringComparison]::OrdinalIgnoreCase)}
  $remove=$legacy -or ($target -match $privateEngine) -or ($owned -and $link.Arguments -match '(?:^|\s)--?private(?:-window)?(?:\s|$)')
  if(!$remove -and !$target){
   # A broken link may resolve to an empty/short path. Its LinkInfo and
   # StringData still carry the original ANSI or Unicode target.
   $raw=[IO.File]::ReadAllBytes($item.FullName)
   $pattern='(?i)[\\/](?:Soul|Sona|SonaGecko)[\\/]engine[\\/]private_browsing\.exe'
   $remove=([Text.Encoding]::ASCII.GetString($raw) -match $pattern) -or ([Text.Encoding]::Unicode.GetString($raw) -match $pattern) -or ($raw.Length -gt 1 -and [Text.Encoding]::Unicode.GetString($raw,1,$raw.Length-1) -match $pattern)
  }
  if($remove){Remove-Item -LiteralPath $item.FullName -Force}
 }
}`
 cleanupLinks = "$env:SONA_LINK_ROOT='" + strings.ReplaceAll(dir, "'", "''") + "';" + cleanupLinks
 if err=core.PowerShell(cleanupLinks);err!=nil{return err}
	if err = core.Shortcuts("Sona", dir, "Sona.exe", strings.TrimPrefix(icon, dir+string(os.PathSeparator)), "", o.Desktop, o.StartMenu); err != nil {
		return err
	}
 // Use a new icon resource path for this release to invalidate Explorer caches.
 refreshIcons := `Add-Type -TypeDefinition 'using System;using System.Text;using System.Runtime.InteropServices;public static class SonaIconRefresh{[DllImport("shell32.dll")]public static extern void SHChangeNotify(uint id,uint flags,IntPtr first,IntPtr second);[DllImport("kernel32.dll",CharSet=CharSet.Unicode)]public static extern uint GetLongPathName(string path,StringBuilder buffer,uint size);public static string Expand(string path){var buffer=new StringBuilder(32768);return GetLongPathName(path,buffer,(uint)buffer.Capacity)>0?buffer.ToString():path;}}'
$shell=New-Object -ComObject WScript.Shell
$roots=@([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'),(Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'))
$exe=$env:SONA_SHORTCUT_EXE
$icon=$env:SONA_SHORTCUT_ICON
foreach($root in $roots){
 foreach($item in (Get-ChildItem -LiteralPath $root -Filter *.lnk -Recurse -File -ErrorAction SilentlyContinue)){
  $link=$shell.CreateShortcut($item.FullName)
  $target=[Environment]::ExpandEnvironmentVariables([string]$link.TargetPath)
  if($target -and [SonaIconRefresh]::Expand($target).Equals([SonaIconRefresh]::Expand($exe),[StringComparison]::OrdinalIgnoreCase)){
   $link.IconLocation=$icon+',0'
   $link.Save()
  }
 }
}
[SonaIconRefresh]::SHChangeNotify(0x08000000,0,[IntPtr]::Zero,[IntPtr]::Zero)
`
 refreshIcons = "$env:SONA_SHORTCUT_EXE='" + strings.ReplaceAll(exe,"'","''") + "';$env:SONA_SHORTCUT_ICON='" + strings.ReplaceAll(icon,"'","''") + "';" + refreshIcons
 if err=core.PowerShell(refreshIcons);err!=nil{return err}
	if err = setReg(uninstallKey, map[string]string{"DisplayName": "Sona Preview 1.160.31", "DisplayVersion": products.Version("sona"), "Publisher": "Sona", "InstallLocation": dir, "DisplayIcon": icon, "UninstallString": `"` + filepath.Join(dir, "Uninstall Sona.exe") + `" --uninstall`}); err != nil {
		return err
	}
 // Register this isolated product without changing Windows UserChoice.
 for _,item:=range []struct{key string;values map[string]string}{
 {`Software\Classes\Sona.URL`,map[string]string{"":"Sona URL","URL Protocol":""}},
 {`Software\Classes\Sona.URL\DefaultIcon`,map[string]string{"":exe+",0"}},
 {`Software\Classes\Sona.URL\shell\open\command`,map[string]string{"":`"`+exe+`" --url "%1"`}},
 {`Software\Clients\StartMenuInternet\Sona`,map[string]string{"":"Sona"}},
 {`Software\Clients\StartMenuInternet\Sona\Capabilities`,map[string]string{"ApplicationName":"Sona","ApplicationDescription":"Sona browser","ApplicationIcon":exe+",0"}},
 {`Software\Clients\StartMenuInternet\Sona\Capabilities\URLAssociations`,map[string]string{"http":"Sona.URL","https":"Sona.URL"}},
 {`Software\RegisteredApplications`,map[string]string{"Sona":`Software\Clients\StartMenuInternet\Sona\Capabilities`}},
 }{if err=setReg(item.key,item.values);err!=nil{return err}}
 // Move previous application profiles into the renamed product, never deleting them.
 oldProfiles:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Soul","Profiles");if _,e:=os.Stat(oldProfiles);os.IsNotExist(e){oldProfiles=filepath.Join(os.Getenv("LOCALAPPDATA"),"SonaGecko","Profiles")};newProfiles:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Sona","Profiles");if _,e:=os.Stat(newProfiles);os.IsNotExist(e){if _,e=os.Stat(oldProfiles);e==nil{if e=os.MkdirAll(filepath.Dir(newProfiles),0700);e!=nil{return e};if e=os.Rename(oldProfiles,newProfiles);e!=nil{return fmt.Errorf("Не удалось перенести прежние профили: %w",e)}}}
 // Remove obsolete registrations of our own prior product only.
 _=registry.DeleteKey(registry.CURRENT_USER,`Software\Microsoft\Windows\CurrentVersion\Uninstall\SonaGecko`)
 // Retire only the verified Preview 12 application, preserving its moved profiles.
 legacyBuild,legacyErr:=os.ReadFile(filepath.Join(legacyDir,"BUILD.json"));var legacy struct{Name string `json:"name"`;Channel string `json:"channel"`};if legacyErr==nil&&json.Unmarshal(legacyBuild,&legacy)==nil&&legacy.Name=="Soul 0.12.0 Preview"&&legacy.Channel=="gecko-preview"{if err=core.RemoveOwned(legacyDir,"soul","Soul.exe");err!=nil{return err};_ = os.Remove(filepath.Join(legacyDir,"Uninstall Soul.exe"));dirs:=[]string{};_ = filepath.WalkDir(legacyDir,func(path string,item os.DirEntry,e error)error{if e==nil&&item.IsDir(){dirs=append(dirs,path)};return nil});for i:=len(dirs)-1;i>=0;i--{_ = os.Remove(dirs[i])};_ = registry.DeleteKey(registry.CURRENT_USER,`Software\Microsoft\Windows\CurrentVersion\Uninstall\Soul`);if key,e:=registry.OpenKey(registry.CURRENT_USER,`Software\RegisteredApplications`,registry.SET_VALUE);e==nil{_ = key.DeleteValue("Soul");key.Close()};_ = setReg(`Software\Classes\Soul.URL\shell\open\command`,map[string]string{"":`"`+exe+`" --url "%1"`});_ = setReg(`Software\Classes\Soul.URL\DefaultIcon`,map[string]string{"":exe+",0"})}
 prefs:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Sona","install-preferences.json");if err=os.MkdirAll(filepath.Dir(prefs),0700);err!=nil{return err};options,_:=json.Marshal(map[string]string{"language":o.Language,"theme":o.Theme});if err=core.AtomicWrite(prefs,options);err!=nil{return err}
	if err = retirePrevious(dir,exe,icon); err != nil { return err }
 if err = removeLoginStartup(dir); err != nil { return err }
	// All profile, theme, language, history and extension data remain untouched.
	a.dir = dir
	a.installed = true
	a.progress.Store(100)
	return nil
}
func (a *Adapter) Remove() error {
	if err := core.RemoveOwned(a.dir, "sona", "Sona.exe"); err != nil {
		return err
	}
	if err := core.Shortcuts("Sona", a.dir, "Sona.exe", "engine/sona/chrome/ui/sona-app-icon.ico", "", false, false); err != nil {
		return err
	}
 script := `foreach($p in @('HKCU:\Software\Classes\Sona.URL','HKCU:\Software\Clients\StartMenuInternet\Sona','HKCU:\` + uninstallKey + `')){if(Test-Path -LiteralPath $p){Remove-Item -LiteralPath $p -Recurse}};Remove-ItemProperty -LiteralPath 'HKCU:\Software\RegisteredApplications' -Name 'Sona' -ErrorAction SilentlyContinue;Remove-ItemProperty -LiteralPath 'HKCU:\Software\Sona' -Name 'InstallDir' -ErrorAction SilentlyContinue;`
	if err := core.PowerShell(script); err != nil {
		return err
	}
	a.progress.Store(100)
	return nil
}



// Remove our existing login registration without touching Firefox or other apps.
func removeLoginStartup(dir string) error {
 for _,path := range []string{`Software\Microsoft\Windows\CurrentVersion\Run`, `Software\Microsoft\Windows\CurrentVersion\RunOnce`} {
  key,err:=registry.OpenKey(registry.CURRENT_USER,path,registry.QUERY_VALUE|registry.SET_VALUE)
  if err==registry.ErrNotExist {continue}; if err!=nil{return err}
  names,err:=key.ReadValueNames(-1);if err!=nil{key.Close();return err}
  for _,name:=range names {
   command,_,e:=key.GetStringValue(name);if e!=nil{continue}
   args,e:=windows.DecomposeCommandLine(command);if e!=nil||len(args)==0{continue}
   target:=filepath.Clean(os.ExpandEnv(args[0]))
   if strings.EqualFold(target,filepath.Join(dir,"Sona.exe"))||strings.EqualFold(target,filepath.Join(dir,"engine","SonaEngine.exe"))||strings.EqualFold(target,filepath.Join(dir,priorName+".exe"))||strings.EqualFold(target,filepath.Join(dir,"engine",priorName+"Engine.exe")) {
    if e=key.DeleteValue(name);e!=nil{key.Close();return e}
   }
  };key.Close()
 };return core.PowerShell(`$ErrorActionPreference='Stop';$targets=@(`+core.QuotePS(filepath.Join(dir,"Sona.exe"))+`,`+core.QuotePS(filepath.Join(dir,"engine","SonaEngine.exe"))+`);$shell=New-Object -ComObject WScript.Shell;foreach($item in (Get-ChildItem -LiteralPath ([Environment]::GetFolderPath('Startup')) -Filter *.lnk -ErrorAction SilentlyContinue)){$target=$shell.CreateShortcut($item.FullName).TargetPath;if($targets -contains $target){Remove-Item -LiteralPath $item.FullName -Force}}`)
}
