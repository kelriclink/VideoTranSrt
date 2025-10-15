add_executable(v2s_cli
    src/main.cpp
)

target_link_libraries(v2s_cli
    PRIVATE
        v2s_core
)

set_target_properties(v2s_cli PROPERTIES OUTPUT_NAME "v2s_cli")