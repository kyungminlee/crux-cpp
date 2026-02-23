cmake_minimum_required(VERSION 3.29)
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
execute_process(
    COMMAND ${CMAKE_COMMAND}
        -B "${SIMPLE_BUILD}"
        -S "${SIMPLE_SRC}"
        -DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}
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
