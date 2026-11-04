//go:build windows
package soulu
import("os";"path/filepath";"testing")
func TestRepairInterruptedAndRemovedInstallations(t *testing.T){
 root:=t.TempDir();if e:=os.MkdirAll(filepath.Join(root,"runtime","empty"),0700);e!=nil{t.Fatal(e)}
 if !repairableDirectory(root){t.Fatal("empty uninstall directories rejected")}
 os.WriteFile(filepath.Join(root,"Uninstall Soulu Gecko.exe"),[]byte("old uninstaller"),0600)
 if !repairableDirectory(root){t.Fatal("legacy uninstaller leftovers rejected")}
 os.WriteFile(filepath.Join(root,"notes.txt"),[]byte("user file"),0600)
 if repairableDirectory(root){t.Fatal("unrelated folder accepted")}
 os.WriteFile(filepath.Join(root,"BUILD.json"),[]byte(`{"name":"Soulu Gecko Preview 8"}`),0600)
 if !repairableDirectory(root){t.Fatal("partial Gecko installation rejected without launcher")}
 os.WriteFile(filepath.Join(root,"BUILD.json"),[]byte(`{"name":"Another browser"}`),0600)
 if repairableDirectory(root){t.Fatal("foreign browser accepted")}
}
