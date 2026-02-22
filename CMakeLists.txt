cmake_minimum_required(VERSION 3.29)
project(extract-cpp)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# On macOS with Homebrew:
#   cmake -B build \
#     -DCMAKE_PREFIX_PATH=$(brew --prefix llvm) \
#     -DCMAKE_CXX_COMPILER=$(brew --prefix llvm)/bin/clang++
if(APPLE)
    # Embed the resource dir so that LibTooling can find clang builtins
    # (stddef.h, cassert, etc.) when re-parsing project sources.
    # LibTooling computes the resource dir from its own binary path, which is
    # wrong for binaries not installed inside the LLVM prefix.
    execute_process(
        COMMAND ${CMAKE_CXX_COMPILER} -print-resource-dir
        OUTPUT_VARIABLE CLANG_RESOURCE_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    execute_process(
        COMMAND xcrun --show-sdk-path
        OUTPUT_VARIABLE APPLE_SDK_PATH
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    add_compile_options(
        -stdlib=libc++
        -resource-dir ${CLANG_RESOURCE_DIR}
        -isysroot ${APPLE_SDK_PATH}
    )
    add_link_options(-stdlib=libc++)
endif()
find_package(LLVM REQUIRED CONFIG)
find_package(Clang REQUIRED CONFIG)

message(STATUS "LLVM ${LLVM_PACKAGE_VERSION} at ${LLVM_DIR}")

add_definitions(${LLVM_DEFINITIONS})

set(CLANG_LINK_LIBS
    clangTooling
    clangIndex
    clangFrontend
    clangSema
    clangAnalysis
    clangEdit
    clangDriver
    clangSerialization
    clangParse
    clangLex
    clangAST
    clangASTMatchers
    clangBasic
)
llvm_map_components_to_libnames(LLVM_LINK_LIBS support core irreader option)

foreach(target def call)
    add_executable(${target} src/${target}.cpp)
    target_include_directories(${target} PRIVATE
        ${LLVM_INCLUDE_DIRS}
        ${CLANG_INCLUDE_DIRS}
    )
    target_link_libraries(${target} PRIVATE ${CLANG_LINK_LIBS} ${LLVM_LINK_LIBS})
endforeach()
