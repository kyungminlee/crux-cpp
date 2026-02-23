cmake_minimum_required(VERSION 3.28)
project(crux-cpp)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(LLVM_ROOT "${CMAKE_PREFIX_PATH}" CACHE PATH
    "LLVM installation root (must contain bin/clang++); defaults to CMAKE_PREFIX_PATH")
find_program(CLANG_CXX_COMPILER clang++ HINTS "${LLVM_ROOT}/bin" NO_DEFAULT_PATH REQUIRED)

# On macOS with Homebrew:
#   cmake -B build \
#     -DCMAKE_PREFIX_PATH=$(brew --prefix llvm) \
#     -DCMAKE_CXX_COMPILER=$(brew --prefix llvm)/bin/clang++
add_subdirectory(cppsrc)

enable_testing()
add_subdirectory(tests)
