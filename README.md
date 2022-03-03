# `ros2_tracing` analysis example

[`ros2_tracing`](https://gitlab.com/ros-tracing/ros2_tracing) system analysis example.
Demonstrates how the ROS 2 instrumentation (in `rclcpp`/`rcl`/`rmw`) and ROS 2 tracing tools (`Trace` launch action) provided by `ros2_tracing` can be leveraged.

It uses:
* the [reference system](https://github.com/ros-realtime/reference-system) proposed by the ROS 2 Real-Time Working Group as an example application
* [`tracetools_analysis`](https://gitlab.com/ros-tracing/tracetools_analysis) in a simple Python script to create simple plots of the execution data
* [Eclipse Trace Compass](https://www.eclipse.org/tracecompass/) to correlate ROS 2 execution information with Linux kernel execution information

This is part of the [`ros2_tracing` paper](https://arxiv.org/abs/2201.00393).
If you use or refer to `ros2_tracing` or this repository, please cite:
<!-- TODO replace with early access/published version when available -->
* C. Bédard, I. Lütkebohle, and M. Dagenais, "ros2_tracing: Multipurpose Low-Overhead Framework for Real-Time Tracing of ROS 2," *arXiv preprint arXiv:2201.00393*, 2022.

BibTeX:

```bibtex
@article{bedard2022ros2tracing,
  title={ros2\_tracing: Multipurpose Low-Overhead Framework for Real-Time Tracing of ROS 2},
  author={B{\'e}dard, Christophe and L{\"u}tkebohle, Ingo and Dagenais, Michel},
  journal={arXiv preprint arXiv:2201.00393},
  year={2022}
}
```

## Timing analysis

1. Set up system to build ROS 2 and enable tracing
    * https://docs.ros.org/en/rolling/Installation/Ubuntu-Development-Setup.html
    * https://gitlab.com/ros-tracing/ros2_tracing
        * Both LTTng userspace and LTTng kernel tracers are required
1. Set up code workspaces and build
    ```sh
    ./setup_workspace.sh
    ```
    * this creates the workspace and builds it in release mode
1. Run example system using launch file
    ```sh
    source analysis_ws/install/setup.bash
    ros2 launch system.launch.py
    ```
    * the launch file ([`system.launch.py`](./system.launch.py)) sets up tracing using the `Trace` launch action and executes the example application
    * trace data will be written to `system-YYYYMMDDTHHMMSS/`
1. Process data and plot results using Python script
    ```sh
    python3 analyze.py system-YYYYMMDDTHHMMSS
    ```
    * plots will be created and saved under the trace directory
        * these plots show various kinds of timing information for the `/BehaviorPlanner` node's input topics, output topics, and periodic callback
    * the Python script will also output information to help locate the `/BehaviorPlanner` node timer callback instance with the longest interval in the trace data (see [*Combined analysis with Linux kernel data*](#combined-analysis-with-Linux-kernel-data)):
        * the callback ID (e.g., `0x013579acdf`)
        * the callback instance index (`[0,N-1]`)

## Combined analysis with Linux kernel data

1. Download and open [Trace Compass](https://www.eclipse.org/tracecompass/)
1. Import userspace and kernel traces from the `system-YYYYMMDDTHHMMSS/` directory
    1. Under *File*, click on *Import...*
    1. Select the root directory of the trace (`system-YYYYMMDDTHHMMSS/`)
    1. Then make sure the trace directory is selected in the filesystem tree view
    1. Click on *Finish*
1. Create experiment (i.e., an aggregation of multiple traces)
    1. In the tree view on the left, under *Traces*, select both traces
    1. Then right click, and, under *Open As Experiment...*, select *Generic Experiment*
1. Open *Control Flow* view
    1. This shows the state of threads over time (running, waiting, etc.) using colours and shows the scheduling switches between threads using arrows
1. In the events tables, find the event corresponding to the timer callback instance of interest using the information in the output of the analysis script
    1. Search in the events table for *Event Type* equal to `ros2:callback_start` with *Contents* containing `callback=0x013579acdf`
    1. Find the right callback instance using the given index by counting the events (starting from an index of 0)
1. Click *Show View Filters* button
    1. Unselect all threads, select the main ROS 2 threads from the application (or at least the thread that generated the timer callback events of interest; see the TID associated with the events)
