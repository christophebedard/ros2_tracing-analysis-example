# `ros2_tracing` analysis example

[`ros2_tracing`](https://gitlab.com/ros-tracing/ros2_tracing) system analysis example.
Uses the [reference system](https://github.com/ros-realtime/reference-system) proposed by the ROS 2 Real-Time Working Group.

## Analysis

1. Set up system to build ROS 2 and enable tracing
    * https://docs.ros.org/en/rolling/Installation/Ubuntu-Development-Setup.html
    * https://gitlab.com/ros-tracing/ros2_tracing
        * LTTng userspace and kernel tracers are required
1. Set up code worksapces and build
    ```sh
    ./setup_workspace.sh
    ```
    * this creates the workspace and builds it in release mode
1. Run example system
    ```sh
    ./run_system.sh
    ```
    * this launches [`system.launch.py`](./system.launch.py)
    * trace data will be written to `system-YYYYMMDDTHHMMSS/`
1. Plot results
    ```sh
    python3 analyze.py system-YYYYMMDDTHHMMSS
    ```
    * plots will be created under the trace directory
