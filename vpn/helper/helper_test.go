package main

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestVLESSPreservesTransports(t *testing.T) {
	for _, kind := range []string{"tcp", "raw", "xhttp", "ws", "grpc"} {
		link := "vless://12345678-1234-1234-1234-123456789abc@example.com:443?security=reality&pbk=public&sid=ab&sni=site.example&type=" + kind + "&path=%2Fstream&host=cdn.example&mode=packet-up&serviceName=rpc&extra=%7B%22xmux%22%3A%7B%22maxConcurrency%22%3A8%7D%7D"
		cfg, engine, e := engineConfig(link, 17890)
		if e != nil || engine != "xray" {
			t.Fatalf("%s: %v", kind, e)
		}
		out := cfg["outbounds"].([]any)[0].(object)
		stream := out["streamSettings"].(object)
		if str(stream, "network") != kind || stream["realitySettings"].(object)["serverName"] != "site.example" {
			t.Fatal("transport/security lost")
		}
		if kind == "xhttp" {
			x := stream["xhttpSettings"].(object)
			if str(x, "path") != "/stream" || str(x, "mode") != "packet-up" || x["extra"] == nil {
				t.Fatal("XHTTP extras lost")
			}
		}
	}
}
func TestSudokuPreservesShortLink(t *testing.T) {
	key := object{"h": "2001:db8::1", "p": float64(443), "k": strings.Repeat("ab", 32), "a": "up_ascii_down_entropy", "e": "chacha20-poly1305", "x": true, "hm": "ws", "ht": true, "hh": "cdn.example", "hy": "/proxy", "hx": "on", "t": "x", "ts": []any{"one", "two"}}
	raw, _ := json.Marshal(key)
	cfg, engine, e := engineConfig("sudoku://"+base64.RawURLEncoding.EncodeToString(raw), 17890)
	if e != nil || engine != "sudoku" {
		t.Fatal(e)
	}
	if cfg["server_address"] != "[2001:db8::1]:443" || cfg["enable_pure_downlink"] != false || cfg["ascii"] != "up_ascii_down_entropy" {
		t.Fatal("Sudoku protocol options lost")
	}
	mask := cfg["httpmask"].(object)
	if mask["tls"] != true || mask["multiplex"] != "on" || mask["path_root"] != "/proxy" {
		t.Fatal("Sudoku HTTP mask lost")
	}
}
func TestRejectInvalidKeys(t *testing.T) {
	for _, link := range []string{"", "http://example.com", "vless://key@example.com:0", "vless://key@example.com:443?security=reality", "sudoku://bad", "sudoku://e30", strings.Repeat("x", 17000)} {
		if _, _, e := engineConfig(link, 17890); e == nil {
			t.Fatal("accepted invalid key")
		}
	}
}
func TestComponentHostsAndTags(t *testing.T) {
	for _, raw := range []string{"http://github.com/a", "https://user:pass@github.com/a", "https://github.com.evil.test/a", "https://localhost/a", "file:///etc/passwd"} {
		u, _ := url.Parse(raw)
		if allowedURL(u) == nil {
			t.Fatal("unsafe source accepted")
		}
	}
	for _, v := range []string{"../x", "v1/../../x", "v1;cmd", ""} {
		if versionPattern.MatchString(v) {
			t.Fatal("unsafe version accepted")
		}
	}
}
func zipBytes(files map[string][]byte) []byte {
	var b bytes.Buffer
	w := zip.NewWriter(&b)
	for name, body := range files {
		f, _ := w.Create(name)
		f.Write(body)
	}
	w.Close()
	return b.Bytes()
}
func TestArchiveRejectsTraversalAndInvalidPE(t *testing.T) {
	for _, files := range []map[string][]byte{{"../xray.exe": []byte("bad")}, {"nested/../../xray.exe": []byte("bad")}, {"C:/xray.exe": []byte("bad")}, {"xray.exe": []byte("not a PE")}, {"xray.exe": []byte("x"), "nested/xray.exe": []byte("x")}} {
		if _, e := extractComponent(zipBytes(files), "xray.exe"); e == nil {
			t.Fatal("unsafe archive accepted")
		}
	}
}

type roundTripFunc func(*http.Request) (*http.Response, error)

func (fn roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) { return fn(r) }
func TestInstallRollbackAndChecksum(t *testing.T) {
	if runtime.GOOS != "windows" {
		t.Skip("real PE fixture is the Windows test executable")
	}
	testExe, _ := os.Executable()
	body, e := os.ReadFile(testExe)
	if e != nil {
		t.Fatal(e)
	}
	root := t.TempDir()
	t.Setenv("LOCALAPPDATA", root)
	previousBase := packageBase
	packageBase = filepath.Join(root, "package")
	defer func() { packageBase = previousBase }()
	os.MkdirAll(filepath.Join(packageBase, "xray"), 0700)
	baseline := filepath.Join(packageBase, "xray", "xray.exe")
	os.WriteFile(baseline, body, 0600)
	sum := sha256.Sum256(body)
	stamp := object{"xray": object{"version": "v1", "sha256": hex.EncodeToString(sum[:])}}
	data, _ := json.Marshal(stamp)
	os.WriteFile(filepath.Join(packageBase, "components.json"), data, 0600)
	archive := zipBytes(map[string][]byte{"xray.exe": body})
	digest := sha256.Sum256(archive)
	release := object{"tag_name": "v2", "draft": false, "assets": []any{object{"name": "Xray-windows-64.zip", "browser_download_url": "https://github.com/XTLS/Xray-core/releases/download/v2/Xray-windows-64.zip", "digest": "sha256:" + hex.EncodeToString(digest[:])}}}
	metadata, _ := json.Marshal(release)
	oldClient := httpClient
	defer func() { httpClient = oldClient }()
	httpClient = &http.Client{Transport: roundTripFunc(func(r *http.Request) (*http.Response, error) {
		payload := metadata
		if r.URL.Host == "github.com" {
			payload = archive
		}
		return &http.Response{StatusCode: 200, Body: io.NopCloser(bytes.NewReader(payload)), Header: http.Header{}}, nil
	})}
	if _, e = installComponent("xray", "v2"); e != nil {
		t.Fatal(e)
	}
	state, e := readComponent("xray")
	if e != nil || state.Current.Version != "v2" || state.Previous.Version != "v1" {
		t.Fatal("version state lost", e)
	}
	path, e := resolveEngine("xray")
	if e != nil || path == baseline {
		t.Fatal("installed core overwrote bundled executable")
	}
	if _, e = manageComponent(object{"component": "xray", "name": "rollback"}); e != nil {
		t.Fatal(e)
	}
	path, e = resolveEngine("xray")
	if e != nil || path != baseline {
		t.Fatal("rollback did not restore bundled version")
	}
	if _, e = manageComponent(object{"component": "xray", "name": "rollback"}); e != nil {
		t.Fatal(e)
	}
	path, _ = resolveEngine("xray")
	os.WriteFile(path, []byte("tampered"), 0600)
	if _, e = resolveEngine("xray"); e == nil {
		t.Fatal("tampered core accepted")
	}
}

func TestLargeReleaseCatalogIsPagedAndProjected(t *testing.T) {
	old := httpClient
	defer func() { httpClient = old }()
	calls := 0
	httpClient = &http.Client{Transport: roundTripFunc(func(r *http.Request) (*http.Response, error) {
		calls++
		if r.URL.Query().Get("per_page") != "20" {
			t.Fatal("unbounded release page")
		}
		page := r.URL.Query().Get("page")
		rows := []object{}
		if page == "1" || page == "2" {
			for i := 0; i < 20; i++ {
				rows = append(rows, object{"tag_name": page + "-" + string(rune('a'+i)), "body": strings.Repeat("x", 240000), "prerelease": page == "1", "assets": []any{object{"name": "Xray-windows-64.zip"}}})
			}
		}
		data, _ := json.Marshal(rows)
		return &http.Response{StatusCode: 200, ContentLength: int64(len(data)), Header: http.Header{}, Body: io.NopCloser(bytes.NewReader(data))}, nil
	})}
	rows, e := catalog("xray")
	if e != nil || len(rows) != 40 || calls != 3 {
		t.Fatalf("paged catalog: %d rows %d calls %v", len(rows), calls, e)
	}
	compact, _ := json.Marshal(rows)
	if len(compact) > 10000 || rows[0]["body"] != nil || rows[0]["assets"] != nil {
		t.Fatal("release bodies leaked into catalog")
	}
}

func TestOfficialReleaseCatalog(t *testing.T) {
	if os.Getenv("SOULU_TEST_LIVE_RELEASES") != "1" {
		t.Skip("explicit live GitHub catalog check")
	}
	for _, id := range []string{"xray", "sudoku"} {
		rows, err := catalog(id)
		if err != nil || len(rows) == 0 {
			t.Fatalf("%s official catalog: %v, %d releases", id, err, len(rows))
		}
		t.Logf("%s: %d official Windows releases, newest %s", id, len(rows), str(rows[0], "tag_name"))
	}
}
