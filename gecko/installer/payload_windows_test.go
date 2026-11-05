//go:build windows
package soulu
import("archive/zip";"bytes";"testing")
func TestPackagedGeckoIntegrityAndTamper(t *testing.T){
 raw,e:=assets.ReadFile("payload.zip");if e!=nil{t.Fatal(e)};if e=verifyGecko(raw);e!=nil{t.Fatal(e)}
 reader,e:=zip.NewReader(bytes.NewReader(raw),int64(len(raw)));if e!=nil{t.Fatal(e)}
 // Re-zip the package with a changed executable; valid ZIP CRC must not defeat SHA checking.
 var b bytes.Buffer;w:=zip.NewWriter(&b)
 for _,f:=range reader.File{if f.Name=="Soul.exe"{n,e:=w.Create(f.Name);if e!=nil{t.Fatal(e)};n.Write([]byte("modified executable"))}else if e=w.Copy(f);e!=nil{t.Fatal(e)}}
 if e=w.Close();e!=nil{t.Fatal(e)};if verifyGecko(b.Bytes())==nil{t.Fatal("changed executable was accepted")}
}
