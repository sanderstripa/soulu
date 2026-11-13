package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestMigrationPreservesPrivateData(t *testing.T) {
	local := t.TempDir()
	root := filepath.Join(local, priorName, "Profiles", "default")
	if e := os.MkdirAll(root, 0700); e != nil {
		t.Fatal(e)
	}
	blobs := map[string][]byte{"cookies.sqlite": {0, 255, 16, 10}, "key4.db": {17, 0, 9}, "logins.json": []byte(`{"encryptedPassword":"unchanged"}`), "places.sqlite": []byte("bookmarks and history")}
	for name, data := range blobs {
		if e := os.WriteFile(filepath.Join(root, name), data, 0600); e != nil {
			t.Fatal(e)
		}
	}
	old := filepath.Join(root, string([]byte{115, 111, 117, 108, 117})+"-settings.json")
	settings := []byte(`{"vpn":{"protected":"encrypted-unchanged"},"settings":{"theme":"dark","startupMode":"` + string([]byte{115, 111, 117, 108, 117}) + `"},"rules":{"sites":{"` + string([]byte{115, 111, 117, 108, 117}) + `.example":{"camera":0}}}}`)
	os.WriteFile(old, settings, 0600)
	component := filepath.Join(root, string([]byte{115, 111, 117, 108, 117})+"-vpn", "Components")
	os.MkdirAll(component, 0700)
	os.WriteFile(filepath.Join(component, "keep"), []byte("downloaded core"), 0600)
	older := filepath.Join(local, "Soul")
	os.MkdirAll(older, 0700)
	os.WriteFile(filepath.Join(older, "older-private-data"), []byte("keep older data"), 0600)
	os.WriteFile(filepath.Join(root, "user.js"), []byte("// "+priorName+" startup policy begin\n// "+priorName+" startup policy end\n"), 0600)
	if e := migrateProductData(local); e != nil {
		t.Fatal(e)
	}
	target := filepath.Join(local, "Sona", "Profiles", "default")
	if data, e := os.ReadFile(filepath.Join(target, "sona-vpn", "Components", "keep")); e != nil || string(data) != "downloaded core" {
		t.Fatal("downloaded VPN component was not migrated", e)
	}
	if data, e := os.ReadFile(filepath.Join(local, "Sona", "PreviousData", "legacy-12", "older-private-data")); e != nil || string(data) != "keep older data" {
		t.Fatal("older data was not preserved", e)
	}
	if data, e := os.ReadFile(filepath.Join(target, "user.js")); e != nil || bytes.Contains(data, []byte(priorName)) {
		t.Fatal("previous startup policy marker remains", e)
	}
	for name, data := range blobs {
		got, e := os.ReadFile(filepath.Join(target, name))
		if e != nil || !bytes.Equal(got, data) {
			t.Fatalf("changed %s: %v", name, e)
		}
	}
	got, e := os.ReadFile(filepath.Join(target, "sona-settings.json"))
	if e != nil || !bytes.Contains(got, []byte("encrypted-unchanged")) {
		t.Fatal("lost settings", e)
	}
	var saved struct {
		Settings struct {
			StartupMode string `json:"startupMode"`
		} `json:"settings"`
		Rules struct {
			Sites map[string]any `json:"sites"`
		} `json:"rules"`
	}
	if json.Unmarshal(got, &saved) != nil || saved.Settings.StartupMode != "sona" || saved.Rules.Sites[string([]byte{115, 111, 117, 108, 117})+".example"] == nil {
		t.Fatal("settings migration changed site rules or startup choice")
	}
	if _, e = os.Stat(filepath.Join(local, priorName)); !os.IsNotExist(e) {
		t.Fatal("previous directory remains")
	}
	if e = migrateProductData(local); e != nil {
		t.Fatal("not idempotent", e)
	}
}
func TestMigrationRefusesTwoDataRoots(t *testing.T) {
	local := t.TempDir()
	for _, name := range []string{priorName, "Sona"} {
		os.MkdirAll(filepath.Join(local, name), 0700)
		os.WriteFile(filepath.Join(local, name, "keep"), []byte(name), 0600)
	}
	if migrateProductData(local) == nil {
		t.Fatal("must refuse collision")
	}
	for _, name := range []string{priorName, "Sona"} {
		if data, e := os.ReadFile(filepath.Join(local, name, "keep")); e != nil || string(data) != name {
			t.Fatal("collision damaged data")
		}
	}
}
