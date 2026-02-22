cmake_minimum_required(VERSION 3.15)
project(simple-example CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build with:
#   cmake -B examples/simple/build examples/simple \
#     -DCMAKE_CXX_COMPILER=$(brew --prefix llvm)/bin/clang++ \
#     -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
if(APPLE)
    execute_process(COMMAND ${CMAKE_CXX_COMPILER} -print-resource-dir
        OUTPUT_VARIABLE CLANG_RESOURCE_DIR OUTPUT_STRIP_TRAILING_WHITESPACE)
    execute_process(COMMAND xcrun --show-sdk-path
        OUTPUT_VARIABLE APPLE_SDK_PATH OUTPUT_STRIP_TRAILING_WHITESPACE)
    add_compile_options(
        -stdlib=libc++
        -resource-dir ${CLANG_RESOURCE_DIR}
        -isysroot ${APPLE_SDK_PATH}
    )
    add_link_options(-stdlib=libc++)
endif()

add_executable(simple shapes.cpp math.cpp storage.cpp main.cpp)
