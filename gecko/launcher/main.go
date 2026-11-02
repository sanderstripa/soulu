// Portable Windows launcher. No registry, system proxy or existing Firefox profile changes.
package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"syscall"
	"unsafe"
)

func fail(s string) {
	p, _ := syscall.UTF16PtrFromString(s)
	t, _ := syscall.UTF16PtrFromString("Soulu Gecko Preview 1")
	syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW").Call(0, uintptr(unsafe.Pointer(p)), uintptr(unsafe.Pointer(t)), 16)
	os.Exit(1)
}
func main() {
	exe, e := os.Executable()
	if e != nil {
		fail(e.Error())
	}
	base := filepath.Dir(exe)
	id := "default"
	args := os.Args[1:]
	if len(args) >= 2 && args[0] == "--profile" {
		id = args[1]
		args = args[2:]
	} else if len(args) > 0 && args[0] == "--private" {
		args = append([]string{"-private-window"}, args[1:]...)
	}
	if !regexp.MustCompile(`^[a-zA-Z0-9_-]{1,64}$`).MatchString(id) {
		fail("Invalid profile identifier")
	}
	root := os.Getenv("LOCALAPPDATA")
	if root == "" {
		fail("LOCALAPPDATA is unavailable")
	}
	profile := filepath.Join(root, "SouluGecko", "Profiles", id)
	if e = os.MkdirAll(profile, 0700); e != nil {
		fail(e.Error())
	}
	cmd := exec.Command(filepath.Join(base, "runtime", "firefox.exe"), append([]string{"-no-remote", "-profile", profile}, args...)...)
	cmd.Dir = base
	if e = cmd.Start(); e != nil {
		fail(e.Error())
	}
	closeJob, e := track(cmd)
	if e != nil {
		cmd.Process.Kill()
		fail("Cannot isolate the browser process tree: " + e.Error())
	}
	defer closeJob()
	cmd.Wait()
}
