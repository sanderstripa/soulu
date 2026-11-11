//go:build windows
package soulu
import("os";"path/filepath";"testing";"golang.org/x/sys/windows/registry")
func TestRepairInterruptedAndRemovedInstallations(t *testing.T){
 root:=t.TempDir();if e:=os.MkdirAll(filepath.Join(root,"runtime","empty"),0700);e!=nil{t.Fatal(e)}
 if !repairableDirectory(root){t.Fatal("empty uninstall directories rejected")}
 os.WriteFile(filepath.Join(root,"Uninstall Soulu.exe"),[]byte("old uninstaller"),0600)
 if !repairableDirectory(root){t.Fatal("legacy uninstaller leftovers rejected")}
 os.WriteFile(filepath.Join(root,"notes.txt"),[]byte("user file"),0600)
 if repairableDirectory(root){t.Fatal("unrelated folder accepted")}
 os.WriteFile(filepath.Join(root,"BUILD.json"),[]byte(`{"name":"Soulu 0.11.0 Preview","channel":"gecko-preview"}`),0600)
 if !repairableDirectory(root){t.Fatal("partial Gecko installation rejected without launcher")}
 os.WriteFile(filepath.Join(root,"BUILD.json"),[]byte(`{"name":"Another browser"}`),0600)
 if repairableDirectory(root){t.Fatal("foreign browser accepted")}
}

func TestAutostartCleanupKeepsOtherApplications(t *testing.T){
 dir:=t.TempDir();key,_,err:=registry.CreateKey(registry.CURRENT_USER,`Software\Microsoft\Windows\CurrentVersion\Run`,registry.QUERY_VALUE|registry.SET_VALUE);if err!=nil{t.Fatal(err)};defer key.Close()
 own:="SouluTest-"+filepath.Base(dir);other:=own+"-Other";defer key.DeleteValue(own);defer key.DeleteValue(other)
 key.SetStringValue(own,`"`+filepath.Join(dir,"engine","SouluEngine.exe")+`" -os-autostart`)
 key.SetStringValue(other,`"C:\Other Browser\firefox.exe" -os-autostart`)
 if err=removeLoginStartup(dir);err!=nil{t.Fatal(err)}
 if _,_,err=key.GetStringValue(own);err!=registry.ErrNotExist{t.Fatal("Soulu autostart remains",err)}
 if _,_,err=key.GetStringValue(other);err!=nil{t.Fatal("unrelated autostart was changed",err)}
}
