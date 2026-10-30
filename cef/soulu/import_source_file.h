#pragma once
#include "examples/soulu/profile_data.h"
#include <windows.h>
#include <stdexcept>

namespace soulu {
// Opening with share-read alone rejects a browser's already-open read/write
// database. Share the handle, then hold a shared byte-range lock while copying:
// readers remain allowed, WriteFile/SQLite writes wait. No source SQLite
// connection, checkpoint or source-side SHM file is ever created.
inline HANDLE OpenImportSourceFile(const std::filesystem::path& path,bool lock) {
  if(!LocalImportPath(path))throw std::runtime_error("Unsupported source path");
  HANDLE h=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
      nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
  if(h==INVALID_HANDLE_VALUE)throw std::runtime_error("Close the source browser and retry: source file is locked or inaccessible");
  try {
    wchar_t final[32768]={};auto n=GetFinalPathNameByHandleW(h,final,32768,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
    if(!n||n>=32768)throw std::runtime_error("Unsupported source path");
    std::wstring resolved(final);
    if(resolved.rfind(L"\\\\?\\UNC\\",0)==0)throw std::runtime_error("Unsupported source path");
    if(resolved.rfind(L"\\\\?\\",0)==0)resolved.erase(0,4);
    if(!LocalImportPath(resolved))throw std::runtime_error("Unsupported source path");
    if(lock){OVERLAPPED position{};bool acquired=false;
      for(int attempt=0;attempt<4;++attempt){if(LockFileEx(h,LOCKFILE_FAIL_IMMEDIATELY,0,MAXDWORD,MAXDWORD,&position)){acquired=true;break;}Sleep(20);}
      if(!acquired)throw std::runtime_error("Close the source browser and retry: source database is busy");
    }
    return h;
  }catch(...){CloseHandle(h);throw;}
}
}
