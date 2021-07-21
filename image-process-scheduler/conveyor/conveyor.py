def build_conveyor(
    primary_config,
    config_path: str,
    config_handle_function,
    pipeline,
    run_function
):
    config = config_handle_function(config_path)
    run_function(pipeline)
