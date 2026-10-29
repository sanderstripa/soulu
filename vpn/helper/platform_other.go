//go:build !windows
package main
import("os";"os/exec";"sync")
var updateMutex sync.Mutex
func hideProcess(cmd *exec.Cmd){}
func replaceFile(from,to string)error{return os.Rename(from,to)}
func updateLock()(func(),error){updateMutex.Lock();return updateMutex.Unlock,nil}
