//go:build windows

package sona

import (
	"connect-installer.local/core/core"
	"encoding/json"
	"fmt"
	"golang.org/x/sys/windows/registry"
	"os"
	"path/filepath"
	"strings"
)

func previousInstallations() []string {
	local := os.Getenv("LOCALAPPDATA")
	roots := []string{filepath.Join(local, "Programs", priorName), filepath.Join(local, "Programs", priorName+"Gecko")}
	if k, e := registry.OpenKey(registry.CURRENT_USER, `Software\`+priorName, registry.QUERY_VALUE); e == nil {
		if dir, _, e := k.GetStringValue("InstallDir"); e == nil && !strings.EqualFold(dir, roots[0]) {
			roots = append(roots, dir)
		}
		k.Close()
	}
	return roots
}
func previousOwned(dir string) bool {
	data, e := os.ReadFile(filepath.Join(dir, "BUILD.json"))
	if e != nil {
		return false
	}
	var build struct {
		Name    string `json:"name"`
		Channel string `json:"channel"`
	}
	return json.Unmarshal(data, &build) == nil && build.Channel == "gecko-preview" && strings.HasPrefix(build.Name, priorName+" ")
}
func checkPreviousClosed() error {
	for _, dir := range previousInstallations() {
		if !previousOwned(dir) {
			continue
		}
		for _, exe := range []string{priorName + ".exe", filepath.Join("engine", priorName+"Engine.exe")} {
			if err := core.CheckClosed(filepath.Join(dir, exe)); err != nil {
				return err
			}
		}
	}
	// Windows profile locks cannot be moved while a previous browser uses them.
	profiles := filepath.Join(os.Getenv("LOCALAPPDATA"), priorName, "Profiles")
	entries, _ := os.ReadDir(profiles)
	for _, entry := range entries {
		if entry.IsDir() {
			lock := filepath.Join(profiles, entry.Name(), "parent.lock")
			if _, e := os.Stat(lock); e == nil {
				f, e := os.OpenFile(lock, os.O_RDWR, 0600)
				if e != nil {
					return fmt.Errorf("close the previous browser before upgrading: %w", e)
				}
				f.Close()
			}
		}
	}
	return nil
}
func retirePrevious(dir, exe, icon string) error {
	for _, oldDir := range previousInstallations() {
		if !previousOwned(oldDir) {
			continue
		}
		if strings.EqualFold(oldDir, dir) {
			return fmt.Errorf("choose the new Sona installation directory")
		}
		// Rewrite only links targeting a verified previous product installation.
		script := `$ErrorActionPreference='Stop';$shell=New-Object -ComObject WScript.Shell;$old=` + core.QuotePS(oldDir) + `;$exe=` + core.QuotePS(exe) + `;$icon=` + core.QuotePS(icon) + `;$oldName=` + core.QuotePS(priorName) + `;
$roots=@([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'),(Join-Path $env:APPDATA 'Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar'));
foreach($root in $roots){foreach($file in (Get-ChildItem -LiteralPath $root -Filter *.lnk -Recurse -File -ErrorAction SilentlyContinue)){
$link=$shell.CreateShortcut($file.FullName);$target=[Environment]::ExpandEnvironmentVariables([string]$link.TargetPath);
if($target.StartsWith($old.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){
# Build a fresh link so hidden properties cannot retain the former app identity.
$tmp=Join-Path $file.DirectoryName (([guid]::NewGuid().ToString('N'))+'.lnk');$fresh=$shell.CreateShortcut($tmp);$fresh.TargetPath=$exe;$fresh.Arguments=$link.Arguments;$fresh.WorkingDirectory=[IO.Path]::GetDirectoryName($exe);$fresh.IconLocation=$icon+',0';$fresh.Description='Sona';$fresh.Save();Move-Item -LiteralPath $tmp -Destination $file.FullName -Force;
$newName=$file.Name.Replace($oldName,'Sona');if($newName -ne $file.Name){$new=Join-Path $file.DirectoryName $newName;if(Test-Path -LiteralPath $new){Remove-Item -LiteralPath $file.FullName -Force}else{Move-Item -LiteralPath $file.FullName -Destination $new}}
}}}`
		if e := core.PowerShell(script); e != nil {
			return e
		}
		if e := removeLoginStartup(oldDir); e != nil {
			return e
		}
		if e := core.RemoveOwned(oldDir, strings.ToLower(priorName), priorName+".exe"); e != nil {
			return e
		}
		if e := os.Remove(filepath.Join(oldDir, "Uninstall "+priorName+".exe")); e != nil && !os.IsNotExist(e) {
			return e
		}
		var dirs []string
		_ = filepath.WalkDir(oldDir, func(path string, entry os.DirEntry, e error) error {
			if e == nil && entry.IsDir() {
				dirs = append(dirs, path)
			}
			return nil
		})
		for i := len(dirs) - 1; i >= 0; i-- {
			_ = os.Remove(dirs[i])
		}
	}
	// Remove only prior product registrations; UserChoice remains Windows-owned.
	script := `$ErrorActionPreference='Stop';$old=` + core.QuotePS(priorName) + `;foreach($path in @(('Software\Classes\'+$old+'.URL'),('Software\Clients\StartMenuInternet\'+$old),('Software\Microsoft\Windows\CurrentVersion\Uninstall\'+$old),('Software\'+$old))){$p='HKCU:\'+$path;if(Test-Path -LiteralPath $p){Remove-Item -LiteralPath $p -Recurse -Force}};Remove-ItemProperty -LiteralPath 'HKCU:\Software\RegisteredApplications' -Name $old -ErrorAction SilentlyContinue;`
	return core.PowerShell(script)
}
