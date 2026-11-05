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

const uninstallKey = `Software\Microsoft\Windows\CurrentVersion\Uninstall\Soul`

// Remove only our uninstaller and empty application directories after exit.
// The shared installer core does not recognize the Gecko uninstaller name.
func (a *Adapter) AfterRemoval() error {
 target,err:=core.OwnedPath(a.dir,"Uninstall Soul.exe");if err!=nil{return err}
 script:=`Wait-Process -Id `+strconv.Itoa(os.Getpid())+` -ErrorAction SilentlyContinue;Start-Sleep -Milliseconds 300;$root=`+core.QuotePS(a.dir)+`;Remove-Item -LiteralPath `+core.QuotePS(target)+` -Force -ErrorAction SilentlyContinue;Get-ChildItem -LiteralPath $root -Directory -Recurse -Force -ErrorAction SilentlyContinue|Sort-Object { $_.FullName.Length } -Descending|ForEach-Object {if(@(Get-ChildItem -LiteralPath $_.FullName -Force).Count -eq 0){Remove-Item -LiteralPath $_.FullName}};if((Test-Path -LiteralPath $root) -and @(Get-ChildItem -LiteralPath $root -Force).Count -eq 0){Remove-Item -LiteralPath $root};`
 cmd:=exec.Command("powershell.exe","-NoProfile","-NonInteractive","-Command",script);cmd.SysProcAttr=&syscall.SysProcAttr{HideWindow:true};return cmd.Start()
}

type Adapter struct {
	dir       string
	progress  atomic.Int32
	installed bool
}

func New() *Adapter {
	dir := filepath.Join(os.Getenv("LOCALAPPDATA"), "Programs", "Soul")
	if k, e := registry.OpenKey(registry.CURRENT_USER, `Software\Soul`, registry.QUERY_VALUE); e == nil {
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
	return exec.Command(filepath.Join(a.dir, "Soul.exe")).Start()
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
 manifest:=entries["soul-engine-manifest.json"];if manifest==nil{return fmt.Errorf("Gecko integrity manifest missing")}
 r,err:=manifest.Open();if err!=nil{return err};var m struct{Name string `json:"name"`; Files []struct{Path string `json:"path"`;SHA string `json:"sha256"`} `json:"files"`};err=json.NewDecoder(io.LimitReader(r,4<<20)).Decode(&m);r.Close();if err!=nil{return err}
 if m.Name!="Soul 0.12.0 Preview"||len(m.Files)<10{return fmt.Errorf("unexpected Gecko payload")}
 checked:=map[string]bool{}
 for _,item:=range m.Files{if len(item.SHA)!=64||checked[item.Path]{return fmt.Errorf("invalid manifest entry")};f:=entries[item.Path];if f==nil||f.FileInfo().IsDir(){return fmt.Errorf("missing Gecko component: %s",item.Path)};r,e:=f.Open();if e!=nil{return e};h:=sha256.New();_,e=io.Copy(h,r);r.Close();if e!=nil{return e};if !strings.EqualFold(hex.EncodeToString(h.Sum(nil)),item.SHA){return fmt.Errorf("Gecko component hash mismatch: %s",item.Path)};checked[item.Path]=true}
 for name,f:=range entries{if !f.FileInfo().IsDir()&&name!="soul-engine-manifest.json"&&!checked[name]{return fmt.Errorf("unverified file: %s",name)}}
 for _,name:=range []string{"Soul.exe","engine/SoulEngine.exe","engine/xul.dll","engine/soulu.cfg","BUILD.json"}{if !checked[name]{return fmt.Errorf("required Gecko component missing: %s",name)}}
 return nil
}
// An interrupted install can lose Soul.exe. Ownership comes from the product
// manifest/build identity, not from the presence of one launcher executable.
func repairableDirectory(dir string) bool {
 if data,e:=os.ReadFile(filepath.Join(dir,core.ManifestName));e==nil{var m core.FileManifest;if json.Unmarshal(data,&m)==nil&&m.Product=="soul"{return true}}
 if data,e:=os.ReadFile(filepath.Join(dir,"BUILD.json"));e==nil{var b struct{Name string `json:"name"`};if json.Unmarshal(data,&b)==nil&&strings.HasPrefix(b.Name,"Soul "){return true}}
 // Older uninstallers leave empty engine folders and their own executable.
 // Ignore these leftovers, while rejecting unrelated files and all links.
 clean:=true
 err:=filepath.WalkDir(dir,func(path string,item os.DirEntry,e error)error{if e!=nil{return e};if item.Type()&os.ModeSymlink!=0{clean=false;return nil};if !item.IsDir()&&path!=filepath.Join(dir,"Uninstall Soul.exe"){clean=false};return nil})
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
	if _, e := os.Stat(filepath.Join(a.dir, "Soul.exe")); e == nil && !strings.EqualFold(dir, a.dir) {
		return fmt.Errorf("update the existing installation at %s", a.dir)
	}
	if entries, e := os.ReadDir(dir); e == nil && len(entries) > 0 {
		if _, e := os.Stat(filepath.Join(dir, "Soul.exe")); e != nil && !repairableDirectory(dir) {
			return fmt.Errorf("В выбранной папке есть посторонние файлы. Выберите отдельную папку для Soulu.")
		}
	}
 // Portable and installed Gecko share profiles: refuse upgrades while either owns one.
 profiles:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Soul","Profiles");if dirs,e:=os.ReadDir(profiles);e==nil{for _,entry:=range dirs{if !entry.IsDir(){continue};lock:=filepath.Join(profiles,entry.Name(),"parent.lock");if _,e=os.Stat(lock);os.IsNotExist(e){continue};name,e:=windows.UTF16PtrFromString(lock);if e!=nil{return e};handle,e:=windows.CreateFile(name,windows.GENERIC_READ,0,nil,windows.OPEN_EXISTING,windows.FILE_ATTRIBUTE_NORMAL,0);if e!=nil{return fmt.Errorf("close Soul before installing: %w",e)};windows.CloseHandle(handle)}}
 // A CEF installation is a different product, even though both use Soul.exe.
 if _,e:=os.Stat(filepath.Join(dir,"Soul.exe"));e==nil{data,e:=os.ReadFile(filepath.Join(dir,"BUILD.json"));if e!=nil{return fmt.Errorf("choose a separate Soul installation folder")};var build struct{Name string `json:"name"`};if json.Unmarshal(data,&build)!=nil||!strings.HasPrefix(build.Name,"Soul "){return fmt.Errorf("this folder belongs to another browser")}}
 geckoProfile:=strings.ToLower(filepath.Join(os.Getenv("LOCALAPPDATA"),"Soul"));if d==geckoProfile||strings.HasPrefix(d,geckoProfile+string(os.PathSeparator)){return fmt.Errorf("profile data cannot be used as an installation folder")}
	// Refuse a running browser. Never invoke taskkill; the user closes it normally.
	if err = core.CheckClosed(filepath.Join(dir, "engine", "SoulEngine.exe"));err!=nil{return err}
	if err = core.CheckClosed(filepath.Join(dir, "Soul.exe")); err != nil {
		return err
	}
	raw, err := assets.ReadFile("payload.zip")
	if err != nil {
		return err
	}
	if err = verifyGecko(raw); err != nil {
		return err
	}
	a.progress.Store(15)
	if err = core.Unpack(raw, dir, "soul", "Soul.exe", func(p int) { a.progress.Store(int32(p)) }); err != nil {
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
	if _, err = core.OwnedPath(dir, "Uninstall Soul.exe"); err != nil {
		return err
	}
	if err = core.AtomicWrite(filepath.Join(dir, "Uninstall Soul.exe"), data); err != nil {
		return err
	}
	if err = setReg(`Software\Soul`, map[string]string{"InstallDir": dir}); err != nil {
		return err
	}
	exe := filepath.Join(dir, "Soul.exe")
	icon := filepath.Join(dir,"engine","soulu","chrome","ui","soulu-app-icon.ico")
	if err = core.Shortcuts("Soul", dir, "Soul.exe", strings.TrimPrefix(icon, dir+string(os.PathSeparator)), "", o.Desktop, o.StartMenu); err != nil {
		return err
	}
	if err = setReg(uninstallKey, map[string]string{"DisplayName": "Soul 0.12.0 Preview", "DisplayVersion": products.Version("soulu"), "Publisher": "Soul", "InstallLocation": dir, "DisplayIcon": exe, "UninstallString": `"` + filepath.Join(dir, "Uninstall Soul.exe") + `" --uninstall`}); err != nil {
		return err
	}
 // Register this isolated product without changing Windows UserChoice.
 for _,item:=range []struct{key string;values map[string]string}{
 {`Software\Classes\Soul.URL`,map[string]string{"":"Soul URL","URL Protocol":""}},
 {`Software\Classes\Soul.URL\DefaultIcon`,map[string]string{"":exe+",0"}},
 {`Software\Classes\Soul.URL\shell\open\command`,map[string]string{"":`"`+exe+`" --url "%1"`}},
 {`Software\Clients\StartMenuInternet\Soul`,map[string]string{"":"Soul"}},
 {`Software\Clients\StartMenuInternet\Soul\Capabilities`,map[string]string{"ApplicationName":"Soul","ApplicationDescription":"Soul browser","ApplicationIcon":exe+",0"}},
 {`Software\Clients\StartMenuInternet\Soul\Capabilities\URLAssociations`,map[string]string{"http":"Soul.URL","https":"Soul.URL"}},
 {`Software\RegisteredApplications`,map[string]string{"Soul":`Software\Clients\StartMenuInternet\Soul\Capabilities`}},
 }{if err=setReg(item.key,item.values);err!=nil{return err}}
 // Move previous application profiles into the renamed product, never deleting them.
 oldProfiles:=filepath.Join(os.Getenv("LOCALAPPDATA"),"SouluGecko","Profiles");newProfiles:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Soul","Profiles");if _,e:=os.Stat(newProfiles);os.IsNotExist(e){if _,e=os.Stat(oldProfiles);e==nil{if e=os.MkdirAll(filepath.Dir(newProfiles),0700);e!=nil{return e};if e=os.Rename(oldProfiles,newProfiles);e!=nil{return fmt.Errorf("Не удалось перенести прежние профили: %w",e)}}}
 // Remove obsolete registrations of our own prior product only.
 _=registry.DeleteKey(registry.CURRENT_USER,`Software\Microsoft\Windows\CurrentVersion\Uninstall\SouluGecko`)
 prefs:=filepath.Join(os.Getenv("LOCALAPPDATA"),"Soul","install-preferences.json");if err=os.MkdirAll(filepath.Dir(prefs),0700);err!=nil{return err};options,_:=json.Marshal(map[string]string{"language":o.Language,"theme":o.Theme});if err=core.AtomicWrite(prefs,options);err!=nil{return err}
	// All profile, theme, language, history and extension data remain untouched.
	a.dir = dir
	a.installed = true
	a.progress.Store(100)
	return nil
}
func (a *Adapter) Remove() error {
	if err := core.RemoveOwned(a.dir, "soul", "Soul.exe"); err != nil {
		return err
	}
	if err := core.Shortcuts("Soul", a.dir, "Soul.exe", "engine/soulu/chrome/ui/soulu-app-icon.ico", "", false, false); err != nil {
		return err
	}
 script := `foreach($p in @('HKCU:\Software\Classes\Soul.URL','HKCU:\Software\Clients\StartMenuInternet\Soul','HKCU:\` + uninstallKey + `')){if(Test-Path -LiteralPath $p){Remove-Item -LiteralPath $p -Recurse}};Remove-ItemProperty -LiteralPath 'HKCU:\Software\RegisteredApplications' -Name 'Soul' -ErrorAction SilentlyContinue;Remove-ItemProperty -LiteralPath 'HKCU:\Software\Soul' -Name 'InstallDir' -ErrorAction SilentlyContinue;`
	if err := core.PowerShell(script); err != nil {
		return err
	}
	a.progress.Store(100)
	return nil
}


