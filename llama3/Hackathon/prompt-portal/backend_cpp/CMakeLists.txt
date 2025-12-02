cmake_minimum_required(VERSION 3.16)
project(prompt_portal_cpp VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Options
option(BUILD_SHARED_LIBS "Build shared libraries" OFF)

# Find required packages
find_package(Threads REQUIRED)

# Include FetchContent for downloading dependencies
include(FetchContent)

# ASIO - Standalone Asio C++ library (required by Crow)
FetchContent_Declare(
    asio
    GIT_REPOSITORY https://github.com/chriskohlhoff/asio.git
    GIT_TAG asio-1-28-0
)

# Crow - Modern C++ micro web framework
FetchContent_Declare(
    Crow
    GIT_REPOSITORY https://github.com/CrowCpp/Crow.git
    GIT_TAG v1.2.0
    CMAKE_ARGS -DCROW_FEATURES="ssl;compression"
)

# nlohmann/json - JSON for Modern C++
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)

# SQLiteCpp - SQLite3 C++ wrapper
FetchContent_Declare(
    SQLiteCpp
    GIT_REPOSITORY https://github.com/SRombauts/SQLiteCpp.git
    GIT_TAG 3.3.1
)

# jwt-cpp - JWT library for C++
FetchContent_Declare(
    jwt-cpp
    GIT_REPOSITORY https://github.com/Thalhammer/jwt-cpp.git
    GIT_TAG v0.7.0
)

# bcrypt - Password hashing
FetchContent_Declare(
    bcrypt
    GIT_REPOSITORY https://github.com/hilch/Bcrypt.cpp.git
    GIT_TAG v1.0.0
)

# Make dependencies available
message(STATUS "Fetching ASIO...")
FetchContent_MakeAvailable(asio)

# Set ASIO include directory for Crow to find
set(ASIO_INCLUDE_DIR ${asio_SOURCE_DIR}/asio/include CACHE PATH "ASIO include directory")

message(STATUS "Fetching Crow...")
set(CROW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(CROW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(Crow)

message(STATUS "Fetching nlohmann/json...")
FetchContent_MakeAvailable(json)

message(STATUS "Fetching SQLiteCpp...")
set(SQLITECPP_RUN_CPPLINT OFF CACHE BOOL "" FORCE)
set(SQLITECPP_RUN_CPPCHECK OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(SQLiteCpp)

message(STATUS "Fetching jwt-cpp...")
FetchContent_MakeAvailable(jwt-cpp)

# Source files
set(SOURCES
    src/main.cpp
    src/database.cpp
    src/auth.cpp
    src/llm_client.cpp
    src/handlers/auth_handler.cpp
    src/handlers/template_handler.cpp
    src/handlers/leaderboard_handler.cpp
    src/handlers/health_handler.cpp
    src/handlers/user_handler.cpp
    src/handlers/llm_handler.cpp
    src/utils/password.cpp
    src/utils/jwt_utils.cpp
    src/middleware/cors.cpp
)

# Header files
set(HEADERS
    include/database.hpp
    include/models.hpp
    include/auth.hpp
    include/config.hpp
    include/llm_client.hpp
    include/handlers/auth_handler.hpp
    include/handlers/template_handler.hpp
    include/handlers/leaderboard_handler.hpp
    include/handlers/health_handler.hpp
    include/handlers/user_handler.hpp
    include/handlers/llm_handler.hpp
    include/utils/password.hpp
    include/utils/jwt_utils.hpp
    include/middleware/cors.hpp
)

# Create executable
add_executable(${PROJECT_NAME} ${SOURCES} ${HEADERS})

# Include directories
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${crow_SOURCE_DIR}/include
    ${json_SOURCE_DIR}/include
    ${SQLiteCpp_SOURCE_DIR}/include
    ${jwt-cpp_SOURCE_DIR}/include
)

# Link libraries
target_link_libraries(${PROJECT_NAME} PRIVATE
    Crow::Crow
    nlohmann_json::nlohmann_json
    SQLiteCpp
    sqlite3
    jwt-cpp::jwt-cpp
    Threads::Threads
)

# Windows-specific settings
if(WIN32)
    target_link_libraries(${PROJECT_NAME} PRIVATE ws2_32 wsock32)
    target_compile_definitions(${PROJECT_NAME} PRIVATE _WIN32_WINNT=0x0A00)
endif()

# Copy config file to build directory
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/config/config.json
    ${CMAKE_CURRENT_BINARY_DIR}/config.json
    COPYONLY
)

# Install
install(TARGETS ${PROJECT_NAME} DESTINATION bin)
install(FILES config/config.json DESTINATION bin)

