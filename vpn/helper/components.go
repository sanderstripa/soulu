package main

import (
	"archive/zip"
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"debug/pe"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

type source struct{ Repo, Archive, Exe string }

var sources = map[string]source{"xray": {"XTLS/Xray-core", "Xray-windows-64.zip", "xray.exe"}, "sudoku": {"SUDOKU-ASCII/sudoku", "sudoku-windows-amd64.zip", "sudoku.exe"}}

type generation struct {
	Version, Slot, SHA256 string
	Bundled               bool
}
type componentState struct{ Current, Previous *generation }

var httpClient = &http.Client{Timeout: 75 * time.Second, CheckRedirect: func(r *http.Request, via []*http.Request) error {
	if len(via) > 8 {
		return errors.New("too many redirects")
	}
	return allowedURL(r.URL)
}}

func allowedURL(u *url.URL) error {
	if u.Scheme != "https" || u.User != nil {
		return errors.New("HTTPS component source required")
	}
	switch strings.ToLower(u.Hostname()) {
	case "api.github.com", "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com":
		return nil
	}
	return errors.New("unapproved component download host")
}
func fetchURL(raw string, max int64) ([]byte, error) {
	u, e := url.Parse(raw)
	if e != nil {
		return nil, e
	}
	if e = allowedURL(u); e != nil {
		return nil, e
	}
	ctx, cancel := context.WithTimeout(context.Background(), 75*time.Second)
	defer cancel()
	request, e := http.NewRequestWithContext(ctx, "GET", u.String(), nil)
	if e != nil {
		return nil, e
	}
	request.Header.Set("User-Agent", "Soulu-Components/1.0.71")
	response, e := httpClient.Do(request)
	if e != nil {
		return nil, e
	}
	defer response.Body.Close()
	if response.StatusCode != 200 {
		return nil, fmt.Errorf("component server HTTP %d", response.StatusCode)
	}
	if response.ContentLength > max {
		return nil, errors.New("component response too large")
	}
	b, e := io.ReadAll(io.LimitReader(response.Body, max+1))
	if int64(len(b)) > max {
		return nil, errors.New("component response too large")
	}
	return b, e
}
func releaseAsset(r object, name string) object {
	assets, _ := r["assets"].([]any)
	for _, v := range assets {
		if a, ok := v.(map[string]any); ok && str(a, "name") == name {
			return a
		}
	}
	return nil
}
func catalog(id string) ([]object, error) {
	source, ok := sources[id]
	if !ok {
		return nil, errors.New("unknown component")
	}
	// Xray's release records contain many platform assets. Keep each response
	// bounded instead of downloading all 100 large records in one request.
	out := []object{}
	seen := map[string]bool{}
	for page := 1; page <= 5; page++ {
		b, e := fetchURL(fmt.Sprintf("https://api.github.com/repos/%s/releases?per_page=20&page=%d", source.Repo, page), 8<<20)
		if e != nil {
			return nil, e
		}
		var rows []object
		if e = json.Unmarshal(b, &rows); e != nil {
			return nil, e
		}
		for _, r := range rows {
			tag := str(r, "tag_name")
			if !boolean(r, "draft") && tag != "" && !seen[tag] && releaseAsset(r, source.Archive) != nil {
				seen[tag] = true
				out = append(out, object{"tag_name": tag, "name": str(r, "name"), "prerelease": boolean(r, "prerelease"), "published_at": str(r, "published_at")})
			}
		}
		if len(rows) < 20 {
			break
		}
	}
	return out, nil
}
func componentRoot(id string) string { return filepath.Join(rootDir(), "Components", id) }
func bundled(id string) (*generation, error) {
	source, ok := sources[id]
	if !ok {
		return nil, errors.New("unknown component")
	}
	_ = source
	b, e := os.ReadFile(filepath.Join(packageDir(), "components.json"))
	if e != nil {
		return nil, e
	}
	var stamps map[string]struct{ Version, SHA256 string }
	if e = json.Unmarshal(b, &stamps); e != nil {
		return nil, e
	}
	v, ok := stamps[id]
	if !ok || len(v.SHA256) != 64 {
		return nil, errors.New("missing bundled component stamp")
	}
	g := &generation{Version: v.Version, SHA256: v.SHA256, Bundled: true}
	_, e = validateGeneration(id, g)
	return g, e
}
func readComponent(id string) (componentState, error) {
	var state componentState
	b, e := os.ReadFile(filepath.Join(componentRoot(id), "active.json"))
	if os.IsNotExist(e) {
		g, e := bundled(id)
		state.Current = g
		return state, e
	}
	if e != nil {
		return state, e
	}
	e = json.Unmarshal(b, &state)
	if e == nil && state.Current == nil {
		e = errors.New("missing active component")
	}
	return state, e
}
func validateGeneration(id string, g *generation) (string, error) {
	source, ok := sources[id]
	if !ok || g == nil || len(g.SHA256) != 64 {
		return "", errors.New("invalid component state")
	}
	path := filepath.Join(packageDir(), id, source.Exe)
	if !g.Bundled {
		if g.Slot == "" || filepath.Base(g.Slot) != g.Slot || strings.ContainsAny(g.Slot, "\\/:") {
			return "", errors.New("unsafe component slot")
		}
		path = filepath.Join(componentRoot(id), g.Slot, source.Exe)
	}
	b, e := os.ReadFile(path)
	if e != nil {
		return "", e
	}
	sum := sha256.Sum256(b)
	if !strings.EqualFold(hex.EncodeToString(sum[:]), g.SHA256) {
		return "", errors.New("component checksum mismatch")
	}
	return path, nil
}
func resolveEngine(id string) (string, error) {
	state, e := readComponent(id)
	if e != nil {
		return "", e
	}
	return validateGeneration(id, state.Current)
}
func saveComponent(id string, state componentState) error {
	root := componentRoot(id)
	if e := os.MkdirAll(root, 0700); e != nil {
		return e
	}
	b, e := json.MarshalIndent(state, "", "  ")
	if e != nil {
		return e
	}
	tmp, e := os.CreateTemp(root, "active-*.tmp")
	if e != nil {
		return e
	}
	name := tmp.Name()
	defer os.Remove(name)
	tmp.Chmod(0600)
	if _, e = tmp.Write(b); e == nil {
		e = tmp.Sync()
	}
	tmp.Close()
	if e != nil {
		return e
	}
	return replaceFile(name, filepath.Join(root, "active.json"))
}

var versionPattern = regexp.MustCompile("^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}$")

func installComponent(id, version string) (object, error) {
	source, ok := sources[id]
	if !ok || !versionPattern.MatchString(version) {
		return nil, errors.New("invalid component or release tag")
	}
	b, e := fetchURL("https://api.github.com/repos/"+source.Repo+"/releases/tags/"+url.PathEscape(version), 4<<20)
	if e != nil {
		return nil, e
	}
	var release object
	if e = json.Unmarshal(b, &release); e != nil {
		return nil, e
	}
	if str(release, "tag_name") != version || boolean(release, "draft") {
		return nil, errors.New("release unavailable")
	}
	asset := releaseAsset(release, source.Archive)
	if asset == nil || !strings.HasPrefix(str(asset, "browser_download_url"), "https://github.com/"+source.Repo+"/releases/download/") {
		return nil, errors.New("official Windows archive missing")
	}
	digest := str(asset, "digest")
	expected := strings.TrimPrefix(digest, "sha256:")
	if len(expected) != 64 || digest == expected {
		return nil, errors.New("official release has no SHA-256 digest; installation refused")
	}
	if _, e = hex.DecodeString(expected); e != nil {
		return nil, e
	}
	archive, e := fetchURL(str(asset, "browser_download_url"), 150<<20)
	if e != nil {
		return nil, e
	}
	sum := sha256.Sum256(archive)
	if !strings.EqualFold(hex.EncodeToString(sum[:]), expected) {
		return nil, errors.New("download SHA-256 mismatch")
	}
	files, e := extractComponent(archive, source.Exe)
	if e != nil {
		return nil, e
	}
	unlock, e := updateLock()
	if e != nil {
		return nil, e
	}
	defer unlock()
	previous, e := readComponent(id)
	if e != nil {
		return nil, e
	}
	random := make([]byte, 8)
	if _, e = rand.Read(random); e != nil {
		return nil, e
	}
	slot := version + "-" + hex.EncodeToString(random)
	dir := filepath.Join(componentRoot(id), slot)
	if e = os.MkdirAll(dir, 0700); e != nil {
		return nil, e
	}
	success := false
	defer func() {
		if !success {
			os.RemoveAll(dir)
		}
	}()
	for name, body := range files {
		if e = os.WriteFile(filepath.Join(dir, name), body, 0600); e != nil {
			return nil, e
		}
	}
	exeSum := sha256.Sum256(files[source.Exe])
	next := &generation{Version: version, Slot: slot, SHA256: hex.EncodeToString(exeSum[:])}
	if e = saveComponent(id, componentState{Current: next, Previous: previous.Current}); e != nil {
		return nil, e
	}
	success = true
	return object{"ok": true, "version": version, "reconnectRequired": true}, nil
}
func extractComponent(archive []byte, exe string) (map[string][]byte, error) {
	z, e := zip.NewReader(bytes.NewReader(archive), int64(len(archive)))
	if e != nil {
		return nil, e
	}
	files := map[string][]byte{}
	var total uint64
	for _, file := range z.File {
		clean := strings.ReplaceAll(file.Name, "\\", "/")
		if strings.HasPrefix(clean, "/") || strings.Contains(clean, "../") || strings.Contains(clean, ":") || file.Mode()&os.ModeSymlink != 0 {
			return nil, errors.New("unsafe ZIP member")
		}
		if file.FileInfo().IsDir() {
			continue
		}
		name := strings.ToLower(filepath.Base(clean))
		if name != exe && name != "geoip.dat" && name != "geosite.dat" && name != "license" && name != "license.txt" {
			continue
		}
		if file.UncompressedSize64 > 128<<20 {
			return nil, errors.New("ZIP member too large")
		}
		total += file.UncompressedSize64
		if total > 300<<20 {
			return nil, errors.New("ZIP expands beyond limit")
		}
		if _, exists := files[name]; exists {
			return nil, errors.New("duplicate ZIP member")
		}
		reader, e := file.Open()
		if e != nil {
			return nil, e
		}
		body, e := io.ReadAll(io.LimitReader(reader, (128<<20)+1))
		reader.Close()
		if e != nil || len(body) > 128<<20 {
			return nil, errors.New("invalid ZIP member")
		}
		files[name] = body
	}
	body := files[exe]
	if len(body) == 0 {
		return nil, errors.New("archive has no core executable")
	}
	binary, e := pe.NewFile(bytes.NewReader(body))
	if e != nil {
		return nil, errors.New("core executable is not a valid Windows PE")
	}
	defer binary.Close()
	if binary.Machine != pe.IMAGE_FILE_MACHINE_AMD64 {
		return nil, errors.New("core executable must be Windows x64")
	}
	return files, nil
}
func manageComponent(r object) (object, error) {
	if boolean(r, "proxy") {
		proxy, _ := url.Parse("socks5://127.0.0.1:17890")
		transport := http.DefaultTransport.(*http.Transport).Clone()
		transport.Proxy = http.ProxyURL(proxy)
		copy := *httpClient
		copy.Transport = transport
		httpClient = &copy
	}
	id := str(r, "component")
	if _, ok := sources[id]; !ok {
		return nil, errors.New("unknown component")
	}
	switch str(r, "name") {
	case "install":
		return installComponent(id, str(r, "version"))
	case "rollback":
		unlock, e := updateLock()
		if e != nil {
			return nil, e
		}
		defer unlock()
		state, e := readComponent(id)
		if e != nil {
			return nil, e
		}
		if state.Previous == nil {
			return nil, errors.New("no previous installed version")
		}
		if _, e = validateGeneration(id, state.Previous); e != nil {
			return nil, e
		}
		state.Current, state.Previous = state.Previous, state.Current
		if e = saveComponent(id, state); e != nil {
			return nil, e
		}
		return object{"ok": true, "version": state.Current.Version, "reconnectRequired": true}, nil
	case "status", "list":
		state, e := readComponent(id)
		out := object{"ok": true, "component": id, "source": "https://github.com/" + sources[id].Repo, "installed": "", "previous": "", "releases": []any{}}
		if e != nil {
			out["error"] = e.Error()
		} else {
			out["installed"] = state.Current.Version
			if state.Previous != nil {
				out["previous"] = state.Previous.Version
			}
		}
		if str(r, "name") == "list" || boolean(r, "check") {
			rows, e := catalog(id)
			if e != nil {
				out["error"] = e.Error()
				return out, nil
			}
			public := []any{}
			for _, v := range rows {
				public = append(public, object{"version": str(v, "tag_name"), "prerelease": boolean(v, "prerelease"), "name": str(v, "name"), "published": str(v, "published_at")})
				if boolean(v, "prerelease") && out["latestPreview"] == nil {
					out["latestPreview"] = str(v, "tag_name")
				}
				if !boolean(v, "prerelease") && out["latestStable"] == nil {
					out["latestStable"] = str(v, "tag_name")
				}
			}
			out["releases"] = public
		}
		return out, nil
	default:
		return nil, errors.New("unsupported component operation")
	}
}
