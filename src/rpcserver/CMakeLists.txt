cmake_minimum_required(VERSION 3.26)
project(rpcserver)
set(TARGET_NAME rpcserver)
set(apple_specific "")

include(ExternalProject)
include_directories(.)
include_directories(protobuf-c)
#add_compile_definitions(DEBUG)
if (NOT DEFINED TARGET)
    message(FATAL_ERROR "Please specify the target using -DTARGET=OSX|IOS|LINUX")
endif ()

# Convert target to uppercase for case-insensitive comparison
string(TOUPPER ${TARGET} TARGET_UPPERCASE)
if ("${TARGET_UPPERCASE}" MATCHES "IOS")
    set(IOS_TARGET ON)
    set(SDK iphoneos)
    set(CMAKE_OSX_ARCHITECTURES arm64 CACHE STRING "Build architecture" FORCE)
    set(ENTITLEMENTS_FILE "${CMAKE_SOURCE_DIR}/ents.plist" CACHE STRING "Path to entitlements file")
    set(TARGET_NAME "${TARGET_NAME}_ios")
    message(STATUS "Entitlements File: ${ENTITLEMENTS_FILE}")
elseif ("${TARGET_UPPERCASE}" MATCHES "OSX")
    set(OSX_TARGET ON)
    set(SDK macosx)
    set(CMAKE_OSX_ARCHITECTURES arm64;x86_64 CACHE STRING "Build architecture" FORCE)
    set(TARGET_NAME "${TARGET_NAME}_macosx")
elseif ("${TARGET_UPPERCASE}" MATCHES "LINUX")
    set(LINUX_TARGET ON)
    set(TARGET_NAME "${TARGET_NAME}_linux")
else ()
    message(FATAL_ERROR "Invalid target specified ${TARGET}. Use -DTARGET=OSX|IOS|LINUX")
endif ()

if ((IOS_TARGET OR OSX_TARGET) AND NOT ${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    message(FATAL_ERROR "Cross-compile is not supported")
elseif (LINUX_TARGET AND NOT ${CMAKE_SYSTEM_NAME} MATCHES "Linux")
    message(FATAL_ERROR "Cross-compile is not supported")
endif ()


# Set CXX_COMPILER and CMAKE_SYSROOT
if (APPLE)
    unset(CMAKE_OSX_DEPLOYMENT_TARGET CACHE)
    execute_process(COMMAND xcrun --sdk ${SDK} --show-sdk-path OUTPUT_VARIABLE CMAKE_OSX_SYSROOT OUTPUT_STRIP_TRAILING_WHITESPACE)
    execute_process(COMMAND xcrun -f --sdk ${SDK} clang OUTPUT_VARIABLE CMAKE_C_COMPILER OUTPUT_STRIP_TRAILING_WHITESPACE)
    set(CMAKE_C_FLAGS -DSAFE_READ_WRITES)
    message(STATUS "CMAKE_OSX_SYSROOT: ${CMAKE_OSX_SYSROOT}")
    message(STATUS "CMAKE_C_COMPILER: ${CMAKE_C_COMPILER}")
endif ()

### Check if protobuf-c source not found and download if necessary
if (NOT EXISTS ${CMAKE_SOURCE_DIR}/protobuf-c)
    message(STATUS "protobuf-c not found, downloading...")
    ExternalProject_Add(
            protobuf-c-download
            PREFIX "protobuf-c-download"
            GIT_REPOSITORY https://github.com/protobuf-c/protobuf-c.git
            GIT_TAG v1.5.0
            SOURCE_DIR ${CMAKE_SOURCE_DIR}/protobuf-c/
            # Disable all other steps
            CONFIGURE_COMMAND ""
            BUILD_COMMAND ""
            INSTALL_COMMAND ""
    )
endif ()
# Build protobuf-c after downloading
set(LIBPROTO_C "${CMAKE_BINARY_DIR}/protobuf-c-build")
# When compiling for multiple architectures in CMake, replace ; with $<SEMICOLON> (e.g., "arm64$<SEMICOLON>x86_64")
string(REPLACE ";" "$<SEMICOLON>" CMAKE_OSX_ARCHITECTURES_ "${CMAKE_OSX_ARCHITECTURES}")
if (EXISTS ${CMAKE_SOURCE_DIR}/protobuf-c)
    message(STATUS "protobuf-c source code found, building...")
    ExternalProject_Add(
            protobuf-c
            PREFIX "protobuf-c-build"
            SOURCE_DIR ${CMAKE_SOURCE_DIR}/protobuf-c/
            BINARY_DIR ${LIBPROTO_C}
            CONFIGURE_COMMAND "${CMAKE_COMMAND}" -DCMAKE_C_COMPILER=${CMAKE_C_COMPILER} -DCMAKE_OSX_SYSROOT=${CMAKE_OSX_SYSROOT} -DCMAKE_OSX_ARCHITECTURES=${CMAKE_OSX_ARCHITECTURES_} "<SOURCE_DIR>/build-cmake"
            BUILD_COMMAND ${CMAKE_MAKE_PROGRAM} protobuf-c
            # Disable all other steps
            INSTALL_COMMAND ""
            DOWNLOAD_COMMAND ""
    )
endif ()
message(STATUS "Target: ${TARGET_NAME}")

if (APPLE)
    # Specify the library paths manually for Apple platforms
    find_library(COREFOUNDATION_LIBRARY
            NAMES CoreFoundation
            PATHS ${CMAKE_OSX_SYSROOT}/System/Library/Frameworks
            NO_DEFAULT_PATH
            NO_CACHE
    )

    find_library(FOUNDATION_LIBRARY
            NAMES Foundation
            PATHS ${CMAKE_OSX_SYSROOT}/System/Library/Frameworks
            NO_DEFAULT_PATH
            NO_CACHE
    )

    # Print the paths for verification
    message("CoreFoundation Library: ${COREFOUNDATION_LIBRARY}")
    message("Foundation Library: ${FOUNDATION_LIBRARY}")

    add_library(darwin_utils OBJECT darwin/darwin_utils.m)
    add_library(darwin_class OBJECT darwin/darwin_class.m)
    add_library(darwin_object OBJECT darwin/darwin_object.m)
    add_library(darwin_get_class_list OBJECT darwin/darwin_get_class_list.m)

    # Add Apple-specific dependencies to the apple_specific variable
    set(apple_specific
            darwin_utils
            darwin_class
            darwin_object
            darwin_get_class_list
            ${COREFOUNDATION_LIBRARY}
            ${FOUNDATION_LIBRARY}
    )

endif ()

add_executable(${TARGET_NAME} rpcserver.c protos/rpc.pb-c.c common.c)
add_dependencies(${TARGET_NAME} protobuf-c)
target_link_libraries(${TARGET_NAME} PRIVATE ${LIBPROTO_C}/libprotobuf-c.a ${apple_specific})

if (IOS_TARGET)
    add_custom_command(
            TARGET ${TARGET_NAME}
            POST_BUILD
            COMMAND codesign -s - --entitlements ${ENTITLEMENTS_FILE} --generate-entitlement-der $<TARGET_FILE:${TARGET_NAME}>
            COMMENT "Signing server binary"
    )
endif ()
