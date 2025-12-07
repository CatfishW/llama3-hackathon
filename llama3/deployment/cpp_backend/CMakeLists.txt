cmake_minimum_required(VERSION 3.16)
project(openai_compat_server VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Options
option(USE_OPENSSL "Enable HTTPS support" OFF)
option(BUILD_STATIC "Build static executable" OFF)

# Dependencies via FetchContent
include(FetchContent)

# cpp-httplib (header-only HTTP/HTTPS library)
FetchContent_Declare(
    httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.15.3
)

# nlohmann/json (header-only JSON library)
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)

FetchContent_MakeAvailable(httplib json)

# Main executable
add_executable(openai_proxy
    src/main.cpp
    src/config.cpp
    src/server.cpp
    src/llama_client.cpp
    src/auth.cpp
    src/utils.cpp
)

target_include_directories(openai_proxy PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(openai_proxy PRIVATE
    httplib::httplib
    nlohmann_json::nlohmann_json
)

# Platform-specific settings
if(WIN32)
    target_link_libraries(openai_proxy PRIVATE ws2_32)
    target_compile_definitions(openai_proxy PRIVATE
        _WIN32_WINNT=0x0601
        WIN32_LEAN_AND_MEAN
    )
elseif(UNIX)
    find_package(Threads REQUIRED)
    target_link_libraries(openai_proxy PRIVATE Threads::Threads)
endif()

if(USE_OPENSSL)
    find_package(OpenSSL REQUIRED)
    target_link_libraries(openai_proxy PRIVATE OpenSSL::SSL OpenSSL::Crypto)
    target_compile_definitions(openai_proxy PRIVATE CPPHTTPLIB_OPENSSL_SUPPORT)
endif()

if(BUILD_STATIC AND NOT WIN32)
    target_link_options(openai_proxy PRIVATE -static-libgcc -static-libstdc++)
endif()

# Install
install(TARGETS openai_proxy RUNTIME DESTINATION bin)

message(STATUS "OpenAI-Compatible Proxy Server (C++ Backend)")
message(STATUS "  HTTPS Support: ${USE_OPENSSL}")
message(STATUS "  Static Build: ${BUILD_STATIC}")

