//go:build windows

package soulu

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

const uninstallKey = `Software\Microsoft\Windows\CurrentVersion\Uninstall\Soulu`

// Remove only our uninstaller and empty application directories after exit.
// The shared installer core does not recognize the Gecko uninstaller name.
func (a *Adapter) AfterRemoval() error {
 target,err:=core.OwnedPath(a.dir,"Uninstall Soulu.exe");if err!=nil{return err}
 script:=`Wait-Process -Id `+strconv.Itoa(os.Getpid())+` -ErrorAction SilentlyContinue;Start-Sleep -Milliseconds 300;$root=`+core.QuotePS(a.dir)+`;Remove-Item -LiteralPath `+core.QuotePS(target)+` -Force -ErrorAction SilentlyContinue;Get-ChildItem -LiteralPath $root -Directory -Recurse -Force -ErrorAction SilentlyContinue|Sort-Object { $_.FullName.Length } -Descending|ForEach-Object {if(@(Get-ChildItem -LiteralPath $_.FullName -Force).Count -eq 0){Remove-Item -LiteralPath $_.FullName}};if((Test-Path -LiteralPath $root) -and @(Get-ChildItem -LiteralPath $root -Force).Count -eq 0){Remove-Item -LiteralPath $root};`
 cmd:=exec.Command("powershell.exe","-NoProfile","-NonInteractive","-Command",script);cmd.SysProcAttr=&syscall.SysProcAttr{HideWindow:true};return cmd.Start()
}

type Adapter struct {
	dir       string
	progress  atomic.Int32
	installed bool
}

func New() *Adapter {
	dir := filepath.Join(os.Getenv("LOCALAPPDATA"), "Programs", "Soulu")
	if k, e := registry.OpenKey(registry.CURRENT_USER, `Software\Soulu`, registry.QUERY_VALUE); e == nil {
		if p, _, e := k.GetStringValue("InstallDir"); e == nil {
			dir = p
		}
		k.Close()
	}
	return &Adapter{dir: dir}
}
func (a *Adapter) Config() core.Config {
	return products.Configure("soulu", a.dir, assets)
}
func (a *Adapter) Progress() core.Progress            { return core.Progress{Percent: int(a.progress.Load())} }
func (a *Adapter) Action(string, []byte) (any, error) { return nil, fmt.Errorf("unknown action") }
func (a *Adapter) Open() error {
	if !a.installed {
		return fmt.Errorf("installation not complete")
	}
	return exec.Command(filepath.Join(a.dir, "Soulu.exe")).Start()
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
 manifest:=entries["soulu-engine-manifest.json"];if manifest==nil{return fmt.Errorf("Gecko integrity manifest missing")}
 r,err:=manifest.Open();if err!=nil{return err};var m struct{Name string `json:"name"`; Files []struct{Path string `json:"path"`;SHA string `json:"sha256"`} `json:"files"`};err=json.NewDecoder(io.LimitReader(r,4<<20)).Decode(&m);r.Close();if err!=nil{return err}
 if m.Name!="Soulu 0.15.0 Preview"||len(m.Files)<10{return fmt.Errorf("unexpected Gecko payload")}
 checked:=map[string]bool{}
 for _,item:=range m.Files{if len(item.SHA)!=64||checked[item.Path]{return fmt.Errorf("invalid manifest entry")};f:=entries[item.Path];if f==nil||f.FileInfo().IsDir(){return fmt.Errorf("missing Gecko component: %s",item.Path)};r,e:=f.Open();if e!=nil{return e};h:=sha256.New();_,e=io.Copy(h,r);r.Close();if e!=nil{return e};if !strings.EqualFold(hex.EncodeToString(h.Sum(nil)),item.SHA){return fmt.Errorf("Gecko component hash mismatch: %s",item.Path)};checked[item.Path]=true}
 for name,f:=range entries{if !f.FileInfo().IsDir()&&name!="soulu-engine-manifest.json"&&!checked[name]{return fmt.Errorf("unverified file: %s",name)}}
 for _,name:=range []string{"Soulu.exe","engine/SouluEngine.exe","engine/xul.dll","engine/soulu.cfg","BUILD.json"}{if !checked[name]{return fmt.Errorf("required Gecko component missing: %s",name)}}
 return nil
}
// An interrupted install can lose Soulu.exe. Ownership comes from the product
// manifest/build identity, not from the presence of one launcher executable.
func repairableDirectory(dir string) bool {
 if data,e:=os.ReadFile(filepath.Join(dir,core.ManifestName));e==nil{var m core.FileManifest;if json.Unmarshal(data,&m)==nil&&m.Product=="soulu"{return true}}
 if data,e:=os.ReadFile(filepath.Join(dir,"BUILD.json"));e==nil{var b struct{Name string `json:"name"`;Channel string `json:"channel"`};if json.Unmarshal(data,&b)==nil&&b.Channel=="gecko-preview"&&strings.HasPrefix(b.Name,"Soulu "){return true}}
 // Older uninstallers leave empty engine folders and their own executable.
 // Ignore these leftovers, while rejecting unrelated files and all links.
 clean:=true
 err:=filepath.WalkDir(dir,func(path string,item os.DirEntry,e error)error{if e!=nil{return e};if item.Type()&os.ModeSymlink!=0{clean=false;return nil};if !item.IsDir()&&path!=filepath.Join(dir,"Uninstall Soulu.exe"){clean=false};return nil})
 return err==nil&&clean
}
func (a *Adapter) Install(o core.Options) error {
	a.progress.Store(0)
	dir, err := core.ValidateDir(o.Path)
	if err != nil {
		return err
	}
	profile := strings.ToLower(filepath.Join(os.Getenv("LOCALAPPDATA"), "Soulu"))
	d := strings.ToLower(dir)
	if d == profile || strings.HasPrefix(d, profile+string(os.PathSeparator)) {
		return fmt.Errorf("the browser profile cannot be used as an installation folder")
	}
	if _, e := os.Stat(filepath.Join(a.dir, "Soulu.exe")); e == nil && !strings.EqualFold(dir, a.dir) {
		return fmt.Errorf("update the existing installation at %s", a.dir)
	}
	if entries, e := os.ReadDir(dir); e == nil && len(entries) > 0 {
		if _, e := os.Stat(filepath.Join(dir, "Soulu.exe")); e != nil && !repairableDirectory(dir) {
			return fmt.Errorf("В выбранной папке есть посторонние файлы. Выберите отдельную папку для Soulu.")
		}
	}
 // Portable and installed Gecko share profiles: refuse upgrades while either owns one.
 profiles:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Soulu","Profiles");if dirs,e:=os.ReadDir(profiles);e==nil{for _,entry:=range dirs{if !entry.IsDir(){continue};lock:=filepath.Join(profiles,entry.Name(),"parent.lock");if _,e=os.Stat(lock);os.IsNotExist(e){continue};name,e:=windows.UTF16PtrFromString(lock);if e!=nil{return e};handle,e:=windows.CreateFile(name,windows.GENERIC_READ,0,nil,windows.OPEN_EXISTING,windows.FILE_ATTRIBUTE_NORMAL,0);if e!=nil{return fmt.Errorf("close Soulu before installing: %w",e)};windows.CloseHandle(handle)}}
 // A CEF installation is a different product, even though both use Soulu.exe.
 if _,e:=os.Stat(filepath.Join(dir,"Soulu.exe"));e==nil{data,e:=os.ReadFile(filepath.Join(dir,"BUILD.json"));if e!=nil{return fmt.Errorf("choose a separate Soulu installation folder")};var build struct{Name string `json:"name"`;Channel string `json:"channel"`};if json.Unmarshal(data,&build)!=nil||(build.Channel!="gecko-preview"||!strings.HasPrefix(build.Name,"Soulu ")){return fmt.Errorf("this folder belongs to another browser")}}
 geckoProfile:=strings.ToLower(filepath.Join(os.Getenv("LOCALAPPDATA"),"Soulu"));if d==geckoProfile||strings.HasPrefix(d,geckoProfile+string(os.PathSeparator)){return fmt.Errorf("profile data cannot be used as an installation folder")}
	// Refuse a running browser. Never invoke taskkill; the user closes it normally.
	if err = core.CheckClosed(filepath.Join(dir, "engine", "SouluEngine.exe"));err!=nil{return err}
	if err = core.CheckClosed(filepath.Join(dir, "Soulu.exe")); err != nil {
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
	a.progress.Store(15)
	if err = core.Unpack(raw, dir, "soulu", "Soulu.exe", func(p int) { a.progress.Store(int32(p)) }); err != nil {
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
	if _, err = core.OwnedPath(dir, "Uninstall Soulu.exe"); err != nil {
		return err
	}
	if err = core.AtomicWrite(filepath.Join(dir, "Uninstall Soulu.exe"), data); err != nil {
		return err
	}
	if err = setReg(`Software\Soulu`, map[string]string{"InstallDir": dir}); err != nil {
		return err
	}
	exe := filepath.Join(dir, "Soulu.exe")
	icon := filepath.Join(dir,"engine","soulu","chrome","ui","soulu-app-icon.ico")
 cleanupLinks:=`$shell=New-Object -ComObject WScript.Shell;$roots=@([Environment]::GetFolderPath('Programs'),[Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('CommonPrograms'));foreach($r in $roots){Get-ChildItem -LiteralPath $r -Filter *.lnk -File -Recurse -ErrorAction SilentlyContinue|ForEach-Object{$link=$shell.CreateShortcut($_.FullName);$target=$link.TargetPath;$private=($_.BaseName -match '^(\u041f\u0440\u0438\u0432\u0430\u0442\u043d\u044b\u0439 \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440|Private Browsing)(?:[ (].*)?$') -or ($_.BaseName -match 'Firefox' -and $_.BaseName -match 'private|\u043f\u0440\u0438\u0432\u0430\u0442') -or ($target -match '(Soul|Soulu|SouluGecko)\\.*private_browsing\.exe$');$old=$target.StartsWith((Join-Path $env:LOCALAPPDATA 'Programs\Soul\'),[StringComparison]::OrdinalIgnoreCase);if($private -or $old){Remove-Item -LiteralPath $_.FullName -Force}}};`
 if err=core.PowerShell(cleanupLinks);err!=nil{return err}
	if err = core.Shortcuts("Soulu", dir, "Soulu.exe", strings.TrimPrefix(icon, dir+string(os.PathSeparator)), "", o.Desktop, o.StartMenu); err != nil {
		return err
	}
	if err = setReg(uninstallKey, map[string]string{"DisplayName": "Soulu 0.15.0 Preview", "DisplayVersion": products.Version("soulu"), "Publisher": "Soulu", "InstallLocation": dir, "DisplayIcon": exe, "UninstallString": `"` + filepath.Join(dir, "Uninstall Soulu.exe") + `" --uninstall`}); err != nil {
		return err
	}
 // Register this isolated product without changing Windows UserChoice.
 for _,item:=range []struct{key string;values map[string]string}{
 {`Software\Classes\Soulu.URL`,map[string]string{"":"Soulu URL","URL Protocol":""}},
 {`Software\Classes\Soulu.URL\DefaultIcon`,map[string]string{"":exe+",0"}},
 {`Software\Classes\Soulu.URL\shell\open\command`,map[string]string{"":`"`+exe+`" --url "%1"`}},
 {`Software\Clients\StartMenuInternet\Soulu`,map[string]string{"":"Soulu"}},
 {`Software\Clients\StartMenuInternet\Soulu\Capabilities`,map[string]string{"ApplicationName":"Soulu","ApplicationDescription":"Soulu browser","ApplicationIcon":exe+",0"}},
 {`Software\Clients\StartMenuInternet\Soulu\Capabilities\URLAssociations`,map[string]string{"http":"Soulu.URL","https":"Soulu.URL"}},
 {`Software\RegisteredApplications`,map[string]string{"Soulu":`Software\Clients\StartMenuInternet\Soulu\Capabilities`}},
 }{if err=setReg(item.key,item.values);err!=nil{return err}}
 // Move previous application profiles into the renamed product, never deleting them.
 oldProfiles:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Soul","Profiles");if _,e:=os.Stat(oldProfiles);os.IsNotExist(e){oldProfiles=filepath.Join(os.Getenv("LOCALAPPDATA"),"SouluGecko","Profiles")};newProfiles:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Soulu","Profiles");if _,e:=os.Stat(newProfiles);os.IsNotExist(e){if _,e=os.Stat(oldProfiles);e==nil{if e=os.MkdirAll(filepath.Dir(newProfiles),0700);e!=nil{return e};if e=os.Rename(oldProfiles,newProfiles);e!=nil{return fmt.Errorf("Не удалось перенести прежние профили: %w",e)}}}
 // Remove obsolete registrations of our own prior product only.
 _=registry.DeleteKey(registry.CURRENT_USER,`Software\Microsoft\Windows\CurrentVersion\Uninstall\SouluGecko`)
 // Retire only the verified Preview 12 application, preserving its moved profiles.
 legacyBuild,legacyErr:=os.ReadFile(filepath.Join(legacyDir,"BUILD.json"));var legacy struct{Name string `json:"name"`;Channel string `json:"channel"`};if legacyErr==nil&&json.Unmarshal(legacyBuild,&legacy)==nil&&legacy.Name=="Soul 0.12.0 Preview"&&legacy.Channel=="gecko-preview"{if err=core.RemoveOwned(legacyDir,"soul","Soul.exe");err!=nil{return err};_ = os.Remove(filepath.Join(legacyDir,"Uninstall Soul.exe"));dirs:=[]string{};_ = filepath.WalkDir(legacyDir,func(path string,item os.DirEntry,e error)error{if e==nil&&item.IsDir(){dirs=append(dirs,path)};return nil});for i:=len(dirs)-1;i>=0;i--{_ = os.Remove(dirs[i])};_ = registry.DeleteKey(registry.CURRENT_USER,`Software\Microsoft\Windows\CurrentVersion\Uninstall\Soul`);if key,e:=registry.OpenKey(registry.CURRENT_USER,`Software\RegisteredApplications`,registry.SET_VALUE);e==nil{_ = key.DeleteValue("Soul");key.Close()};_ = setReg(`Software\Classes\Soul.URL\shell\open\command`,map[string]string{"":`"`+exe+`" --url "%1"`});_ = setReg(`Software\Classes\Soul.URL\DefaultIcon`,map[string]string{"":exe+",0"})}
 prefs:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Soulu","install-preferences.json");if err=os.MkdirAll(filepath.Dir(prefs),0700);err!=nil{return err};options,_:=json.Marshal(map[string]string{"language":o.Language,"theme":o.Theme});if err=core.AtomicWrite(prefs,options);err!=nil{return err}
	// All profile, theme, language, history and extension data remain untouched.
	a.dir = dir
	a.installed = true
	a.progress.Store(100)
	return nil
}
func (a *Adapter) Remove() error {
	if err := core.RemoveOwned(a.dir, "soulu", "Soulu.exe"); err != nil {
		return err
	}
	if err := core.Shortcuts("Soulu", a.dir, "Soulu.exe", "engine/soulu/chrome/ui/soulu-app-icon.ico", "", false, false); err != nil {
		return err
	}
 script := `foreach($p in @('HKCU:\Software\Classes\Soulu.URL','HKCU:\Software\Clients\StartMenuInternet\Soulu','HKCU:\` + uninstallKey + `')){if(Test-Path -LiteralPath $p){Remove-Item -LiteralPath $p -Recurse}};Remove-ItemProperty -LiteralPath 'HKCU:\Software\RegisteredApplications' -Name 'Soulu' -ErrorAction SilentlyContinue;Remove-ItemProperty -LiteralPath 'HKCU:\Software\Soulu' -Name 'InstallDir' -ErrorAction SilentlyContinue;`
	if err := core.PowerShell(script); err != nil {
		return err
	}
	a.progress.Store(100)
	return nil
}


