package main

import (
	"os/exec"
	"syscall"
	"unsafe"
)

// Kill descendants, including VPN cores, if the portable launcher terminates.
// Modern Windows allows Firefox's nested sandbox jobs inside this job.
type basicLimits struct {
	PerProcessUserTimeLimit, PerJobUserTimeLimit int64
	LimitFlags                                   uint32
	MinimumWorkingSetSize, MaximumWorkingSetSize uintptr
	ActiveProcessLimit                           uint32
	Affinity                                     uintptr
	PriorityClass, SchedulingClass               uint32
}
type ioCounters struct{ ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount uint64 }
type extendedLimits struct {
	Basic                                                                        basicLimits
	IO                                                                           ioCounters
	ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed uintptr
}

func track(cmd *exec.Cmd) (func(), error) {
	kernel := syscall.NewLazyDLL("kernel32.dll")
	job, _, e := kernel.NewProc("CreateJobObjectW").Call(0, 0)
	if job == 0 {
		return nil, e
	}
	closeJob := func() { kernel.NewProc("CloseHandle").Call(job) }
	limits := extendedLimits{}
	limits.Basic.LimitFlags = 0x2000
	ok, _, e := kernel.NewProc("SetInformationJobObject").Call(job, 9, uintptr(unsafe.Pointer(&limits)), unsafe.Sizeof(limits))
	if ok == 0 {
		closeJob()
		return nil, e
	}
	process, _, e := kernel.NewProc("OpenProcess").Call(0x0100|0x0001, 0, uintptr(cmd.Process.Pid))
	if process == 0 {
		closeJob()
		return nil, e
	}
	defer kernel.NewProc("CloseHandle").Call(process)
	ok, _, e = kernel.NewProc("AssignProcessToJobObject").Call(job, process)
	if ok == 0 {
		closeJob()
		return nil, e
	}
	return closeJob, nil
}
