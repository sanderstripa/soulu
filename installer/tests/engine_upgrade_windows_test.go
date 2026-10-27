//go:build windows

package soulu

import (
 "archive/zip"
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "testing"
)

// Exercise the installed adapter's actual verifier, including fail-closed paths.
func engineFixture(t *testing.T, distribution, fault string) []byte {
 t.Helper()
 var buffer bytes.Buffer
 zw := zip.NewWriter(&buffer)
 files := []map[string]string{}
 for i := 0; i < 5; i++ {
  name := fmt.Sprintf("component-%d", i)
  data := []byte(name)
  hash := sha256.Sum256(data)
  digest := hex.EncodeToString(hash[:])
  if fault == "hash" && i == 0 { digest = "invalid" }
  files = append(files, map[string]string{"path": name, "sha256": digest})
  if fault == "missing-file" && i == 0 { continue }
  w, err := zw.Create(name); if err != nil { t.Fatal(err) }
  if _, err = w.Write(data); err != nil { t.Fatal(err) }
 }
 if fault != "missing-manifest" {
  w, err := zw.Create("cef-runtime-manifest.json"); if err != nil { t.Fatal(err) }
  if err = json.NewEncoder(w).Encode(map[string]any{"distribution": distribution, "files": files}); err != nil { t.Fatal(err) }
 }
 if err := zw.Close(); err != nil { t.Fatal(err) }
 return buffer.Bytes()
}

func TestEngineUpgradeRejectsWrongOrDamagedPayload(t *testing.T) {
 const approved = "156.0.14+g4fa4ab5+chromium-156.0.8078.48"
 if err := verifyCEF(engineFixture(t, approved, "")); err != nil { t.Fatal(err) }
 for _, fault := range []string{"hash", "missing-file", "missing-manifest"} {
  t.Run(fault, func(t *testing.T) {
   if verifyCEF(engineFixture(t, approved, fault)) == nil { t.Fatal("damaged payload accepted") }
  })
 }
 if verifyCEF(engineFixture(t, "154.0.33+ga03e714+chromium-154.0.8037.94", "")) == nil {
  t.Fatal("previous engine distribution accepted")
 }
}
