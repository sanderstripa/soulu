# Soulu native CEF shell. This directory is copied into cef-project/examples
# by the Windows workflow, so it intentionally uses cef-project's helpers.
set(SOULU_SRCS
  soulu_menu.h
  soulu_menu.cc
  isolated_page_job.h
  isolated_page_job.cc
  translation.cc
  translation_model_download.h
  translation_model_download.cc
  app_factory.h
  app_browser.cc
  app_renderer.cc
  app_other.cc
  browser_client.h
  browser_client.cc
  browser_window.h
  browser_window.cc
  settings_session.cc
  settings_overlay.h
  motion.h
  settings_overlay.cc
  home_page.cc
  onboarding.cc
  home_weather.h
  profile_data.h
  history_store.h
  history_store.cc
  history_page.cc
  clear_data.h
  clear_data.cc
  profile_data.cc
  adblock_bridge.h
  adblock_bridge.cc
  password_import.cc
  data_tests.cc
  frosted_backdrop.h
  frosted_backdrop.cc
  shell_surface.h
  shell_surface.cc
  main.cc
  typography_native.h
  typography_native.cc
  typography_metrics.h
  resource.h
  win/resource.rc
)

# CEF appends /std:c++17 in its target flags; normalize it before its
# helpers run so that it cannot override CXX_STANDARD for C++/WinRT.
string(REPLACE "/std:c++17" "/std:c++20" CEF_COMPILER_FLAGS "${CEF_COMPILER_FLAGS}")
string(REPLACE "/std:c++17" "/std:c++20" CEF_CXX_COMPILER_FLAGS "${CEF_CXX_COMPILER_FLAGS}")
set(EXAMPLE_TARGET "soulu")
SET_EXAMPLE_SOURCE_GROUPS("${SOULU_SRCS}")

if(USE_SANDBOX)
  add_library(${EXAMPLE_TARGET} SHARED ${SOULU_SRCS})
  SET_EXAMPLE_LIBRARY_TARGET_PROPERTIES(${EXAMPLE_TARGET})
  COPY_SINGLE_FILE(${EXAMPLE_TARGET} ${CEF_BINARY_DIR}/bootstrap.exe ${EXAMPLE_TARGET_OUT_DIR}/${EXAMPLE_TARGET}.exe)
else()
  add_executable(${EXAMPLE_TARGET} WIN32 ${SOULU_SRCS})
  SET_EXAMPLE_EXECUTABLE_TARGET_PROPERTIES(${EXAMPLE_TARGET})
endif()

find_program(CARGO_EXECUTABLE cargo REQUIRED)
set(ADBLOCK_LIB "${CMAKE_CURRENT_BINARY_DIR}/adblock/release/soulu_adblock.lib")
file(GLOB_RECURSE ADBLOCK_INPUTS CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/adblock/src/*.rs" "${CMAKE_CURRENT_SOURCE_DIR}/adblock/filters/*.txt")
add_custom_command(OUTPUT "${ADBLOCK_LIB}"
  COMMAND ${CARGO_EXECUTABLE} build --locked --release --manifest-path "${CMAKE_CURRENT_SOURCE_DIR}/adblock/Cargo.toml" --target-dir "${CMAKE_CURRENT_BINARY_DIR}/adblock"
  DEPENDS ${ADBLOCK_INPUTS} adblock/Cargo.toml adblock/Cargo.lock
  VERBATIM)
add_custom_target(soulu_adblock_build DEPENDS "${ADBLOCK_LIB}")
add_library(soulu_adblock STATIC IMPORTED)
set_target_properties(soulu_adblock PROPERTIES IMPORTED_LOCATION "${ADBLOCK_LIB}")
add_dependencies(soulu_adblock soulu_adblock_build)
add_dependencies(${EXAMPLE_TARGET} shared soulu_adblock_build)
enable_language(C)
add_library(soulu_sqlite STATIC third_party/sqlite3.c)
if(MSVC)
  target_compile_options(soulu_sqlite PRIVATE ${CEF_RUNTIME_LIBRARY_FLAG})
endif()
target_compile_definitions(soulu_sqlite PRIVATE SQLITE_OMIT_LOAD_EXTENSION SQLITE_DQS=0 SQLITE_SECURE_DELETE=1)
target_link_libraries(${EXAMPLE_TARGET} shared soulu_sqlite soulu_adblock userenv ntdll secur32 crypt32 bcrypt dwmapi ws2_32 advapi32 shell32 ole32 oleaut32 oleacc uuid windowsapp CoreMessaging)
target_compile_definitions(${EXAMPLE_TARGET} PRIVATE UNICODE _UNICODE NOMINMAX WIN32_LEAN_AND_MEAN)
if(MSVC)
  target_compile_options(${EXAMPLE_TARGET} PRIVATE /utf-8 /EHsc /Zc:__cplusplus)
  target_link_options(${EXAMPLE_TARGET} PRIVATE "/MANIFEST:EMBED" "/MANIFESTINPUT:${CMAKE_CURRENT_SOURCE_DIR}/win/soulu.manifest")
endif()
set_target_properties(${EXAMPLE_TARGET} PROPERTIES OUTPUT_NAME "Soulu" CXX_STANDARD 20 CXX_STANDARD_REQUIRED YES)

# Use this distribution's own file lists, including architecture-specific DLLs.
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/cef-runtime-list.txt"
     "${CEF_BINARY_FILES};${CEF_RESOURCE_FILES}")

add_custom_command(TARGET ${EXAMPLE_TARGET} POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy
          "${CMAKE_CURRENT_BINARY_DIR}/cef-runtime-list.txt"
          "$<TARGET_FILE_DIR:${EXAMPLE_TARGET}>/cef-runtime-list.txt"
  COMMAND ${CMAKE_COMMAND} -E copy_directory
          "${CMAKE_CURRENT_SOURCE_DIR}/assets/ui"
          "$<TARGET_FILE_DIR:${EXAMPLE_TARGET}>/ui"
  COMMAND ${CMAKE_COMMAND} -E copy_directory
          "${CMAKE_CURRENT_SOURCE_DIR}/assets/vpn"
          "$<TARGET_FILE_DIR:${EXAMPLE_TARGET}>/vpn"
  COMMAND ${CMAKE_COMMAND} -E copy_directory
          "${CMAKE_CURRENT_SOURCE_DIR}/adblock/notices"
          "$<TARGET_FILE_DIR:${EXAMPLE_TARGET}>/licenses/adblock"
  COMMAND ${CMAKE_COMMAND} -E copy_directory
          "${CMAKE_CURRENT_SOURCE_DIR}/assets/ui/third_party/notices"
          "$<TARGET_FILE_DIR:${EXAMPLE_TARGET}>/licenses/translation"
  COMMAND ${CMAKE_COMMAND} -E copy
          "${CMAKE_CURRENT_SOURCE_DIR}/assets/ui/third_party/bergamot.LICENSE"
          "$<TARGET_FILE_DIR:${EXAMPLE_TARGET}>/licenses/translation/bergamot.LICENSE"
  COMMAND ${CMAKE_COMMAND} -E copy
          "${CMAKE_CURRENT_SOURCE_DIR}/assets/ui/third_party/tinyld.LICENSE"
          "$<TARGET_FILE_DIR:${EXAMPLE_TARGET}>/licenses/translation/tinyld.LICENSE"
  VERBATIM)

# Preview 25 snapshot publishing keeps ordinary CEF validation unchanged.
