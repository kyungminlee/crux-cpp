cmake_minimum_required(VERSION 3.28)
project(crux-cpp)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# On macOS with Homebrew:
#   cmake -B build \
#     -DCMAKE_PREFIX_PATH=$(brew --prefix llvm) \
#     -DCMAKE_CXX_COMPILER=$(brew --prefix llvm)/bin/clang++
add_subdirectory(cppsrc)

# ── Tests ─────────────────────────────────────────────────────────────────────

enable_testing()

set(SIMPLE_SRC "${CMAKE_SOURCE_DIR}/tests/simple")
set(SIMPLE_BUILD "${CMAKE_BINARY_DIR}/tests/simple")
set(SIMPLE_SRCS
    "${SIMPLE_SRC}/shapes.cpp"
    "${SIMPLE_SRC}/math.cpp"
    "${SIMPLE_SRC}/storage.cpp"
    "${SIMPLE_SRC}/main.cpp"
)

# Configure tests/simple at cmake configure time to produce compile_commands.json.
# compile_commands.json must use a clang++ that LibTooling understands natively, so
# that system headers (e.g. <cmath>) are found when re-parsing. The sub-project is
# only configured (never built), so the clang++/libstdc++ linker path issue is moot.
set(LLVM_ROOT "${CMAKE_PREFIX_PATH}" CACHE PATH
    "LLVM installation root (must contain bin/clang++); defaults to CMAKE_PREFIX_PATH")
find_program(SIMPLE_CXX clang++ HINTS "${LLVM_ROOT}/bin" NO_DEFAULT_PATH REQUIRED)
execute_process(
    COMMAND ${CMAKE_COMMAND}
        -B "${SIMPLE_BUILD}"
        -S "${SIMPLE_SRC}"
        -DCMAKE_CXX_COMPILER=${SIMPLE_CXX}
        -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    OUTPUT_QUIET
)

foreach(tool def call class)
    add_test(
        NAME ${tool}_simple
        COMMAND bash "${CMAKE_SOURCE_DIR}/tests/run_test.sh"
            $<TARGET_FILE:${tool}>
            "${SIMPLE_SRC}/expected_${tool}.csv"
            "${SIMPLE_BUILD}"
            "${SIMPLE_SRC}"
            ${SIMPLE_SRCS}
    )
endforeach()
