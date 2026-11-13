package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Prior product identity is used only to locate existing user data.
var priorName = string([]byte{83, 111, 117, 108, 117})

// Rename the complete root atomically on the same volume. Never merge profiles:
// collisions must be resolved without overwriting either user's data.
func migrateProductData(local string) error {
	target := filepath.Join(local, "Sona")
	for _, name := range []string{priorName, "Soul", priorName + "Gecko"} {
		source := filepath.Join(local, name)
		info, err := os.Lstat(source)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return err
		}
		if !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("unsafe previous profile directory")
		}
		if _, err = os.Stat(target); os.IsNotExist(err) {
			if err = os.Rename(source, target); err != nil {
				return err
			}
		} else if err != nil {
			return err
		} else {
			// A previous migration may already have moved this root. Empty old roots
			// are harmless, but two populated roots must never be combined silently.
			entries, e := os.ReadDir(source)
			if e != nil {
				return e
			}
			if len(entries) > 0 {
				return fmt.Errorf("two browser data folders exist; preserve both and resolve before upgrade")
			}
			if e = os.Remove(source); e != nil {
				return e
			}
		}
	}
	if _, err := os.Stat(target); os.IsNotExist(err) {
		return nil
	}
	marker := filepath.Join(target, ".sona-identity-v31")
	if _, e := os.Stat(marker); e == nil {
		return nil
	}
	old := strings.ToLower(priorName)
	var paths []string
	var directories []string
	err := filepath.WalkDir(target, func(path string, item os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if item.Type()&os.ModeSymlink != 0 {
			return fmt.Errorf("linked profile entry cannot be migrated: %s", path)
		}
		if item.IsDir() {
			if strings.HasPrefix(item.Name(), old+"-") || strings.HasPrefix(item.Name(), priorName+"-") {
				directories = append(directories, path)
			}
			return nil
		}
		if strings.HasPrefix(item.Name(), old+"-") || strings.HasPrefix(item.Name(), priorName+"-") {
			paths = append(paths, path)
		}
		return nil
	})
	if err != nil {
		return err
	}
	for _, path := range paths {
		name := filepath.Base(path)
		next := strings.ReplaceAll(strings.ReplaceAll(name, old, "sona"), priorName, "Sona")
		dest := filepath.Join(filepath.Dir(path), next)
		if _, err = os.Stat(dest); err == nil {
			return fmt.Errorf("profile migration destination already exists: %s", dest)
		} else if !os.IsNotExist(err) {
			return err
		}
		// Keep encrypted settings values and arbitrary user strings byte-for-byte.
		// Only identifiers in product-owned JSON objects change.
		if strings.HasSuffix(name, "-settings.json") {
			data, e := os.ReadFile(path)
			if e != nil {
				return e
			}
			var value any
			if json.Unmarshal(data, &value) != nil {
				return fmt.Errorf("invalid saved browser settings")
			}
			var convert func(any) any
			convert = func(v any) any {
				switch x := v.(type) {
				case map[string]any:
					r := map[string]any{}
					for k, item := range x {
						if (k == "startupMode" || k == "newTabMode" || k == "homeMode") && item == old {
							r[k] = "sona"
						} else {
							r[k] = convert(item)
						}
					}
					return r
				case []any:
					for i, item := range x {
						x[i] = convert(item)
					}
					return x
				case string:
					if strings.HasPrefix(x, old+"://") {
						return "sona" + x[len(old):]
					}
					return x
				}
				return v
			}
			data, e = json.Marshal(convert(value))
			if e != nil {
				return e
			}
			// Write the new file before deleting the previous one.
			if e = os.WriteFile(dest, data, 0600); e != nil {
				return e
			}
			if e = os.Remove(path); e != nil {
				return e
			}
		} else if err = os.Rename(path, dest); err != nil {
			return err
		}
	}
	// Rename owned component/cache directories after their files, deepest first.
	for i := len(directories) - 1; i >= 0; i-- {
		source := directories[i]
		name := filepath.Base(source)
		next := strings.ReplaceAll(strings.ReplaceAll(name, old, "sona"), priorName, "Sona")
		dest := filepath.Join(filepath.Dir(source), next)
		if _, e := os.Stat(dest); e == nil {
			return fmt.Errorf("component migration destination already exists: %s", dest)
		} else if !os.IsNotExist(e) {
			return e
		}
		if e := os.Rename(source, dest); e != nil {
			return e
		}
	}
	// Compiled chrome contains absolute paths and must be rebuilt for Sona.
	profiles := filepath.Join(target, "Profiles")
	entries, _ := os.ReadDir(profiles)
	for _, entry := range entries {
		if entry.IsDir() {
			if err = os.RemoveAll(filepath.Join(profiles, entry.Name(), "startupCache")); err != nil {
				return err
			}
		}
	}
	return os.WriteFile(marker, []byte("Sona"), 0600)
}
