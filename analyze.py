#!/usr/bin/env python3
# Copyright 2021 Christophe Bedard
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ROS 2 system example analysis script, see README."""

import itertools
import os
import sys
from typing import List
from typing import Optional
from typing import Tuple

import matplotlib.pyplot as plt

import numpy as np

import pandas as pd

# Add paths to tracetools_analysis and tracetools_read, assuming a workspace with:
#   src/tracetools_analysis/
#   src/ros-tracing/ros2_tracing/tracetools_read/
src_dir = 'analysis_ws/src'
sys.path.insert(0, os.path.join(src_dir, 'tracetools_analysis/tracetools_analysis'))
sys.path.insert(0, os.path.join(src_dir, 'ros-tracing/ros2_tracing/tracetools_read'))

from tracetools_analysis.loading import load_file  # noqa: E402
from tracetools_analysis.processor.ros2 import Ros2Handler  # noqa: E402
from tracetools_analysis.utils.ros2 import Ros2DataModelUtil  # noqa: E402


# Parameters
to_svg = True
include_plot_title = False


trace_name = None
data_util = None
callback_symbols = None
TimeRange = Tuple[pd.Timestamp, pd.Timestamp, pd.Timedelta]
TimeRanges = List[TimeRange]


def get_handle(handle_type: str, name: str) -> int:
    """Get handle from name and type."""
    if handle_type == 'pub':
        pub_handles = data_util.data.rcl_publishers.loc[
            data_util.data.rcl_publishers['topic_name'] == name
        ].index.values.astype(int)
        # For this demo, we don't expect more than 1 publisher per topic
        assert 1 == len(pub_handles)
        return pub_handles[0]
    if handle_type == 'sub':
        sub_handles = data_util.data.rcl_subscriptions.loc[
            data_util.data.rcl_subscriptions['topic_name'] == name
        ].index.values.astype(int)
        # For this demo, we don't expect more than 1 subscription per topic
        assert 1 == len(sub_handles), f'len={len(sub_handles)}'
        return sub_handles[0]
    if handle_type == 'node':
        node_handles = data_util.data.nodes.loc[
            data_util.data.nodes['name'] == name
        ].index.values.astype(int)
        assert 1 == len(node_handles), f'len={len(node_handles)}'
        return node_handles[0]
    assert False, 'unknown handle_type value'


# def get_pub_sub_creation_time(handle_type: str, topic_name: str) -> pd.Timestamp:
#     # Get handle
#     handle = get_handle(handle_type, topic_name)

#     df = None
#     if handle_type == 'pub':
#         # Get timestamp from rcl_publisher_init
#         df = data_util.convert_time_columns(data_util.data.rcl_publishers, [], ['timestamp'], False)
#     elif handle_type == 'sub':
#         # Get timestamp from rcl_subscription_init
#         df = data_util.convert_time_columns(data_util.data.rcl_subscriptions, [], ['timestamp'], False)
#     else:
#         assert False, 'unknown handle_type value'
#     return df.loc[handle, 'timestamp']


# def get_timer_creation_time(node_name: str) -> pd.Timestamp:
#     # Get handle
#     node_handle = get_handle('node', node_name)

#     # Get timer handle from timer-node links
#     timer_node_links = data_util.data.timer_node_links.loc[
#         data_util.data.timer_node_links['node_handle'] == node_handle
#     ].index.values.astype(int)
#     assert 1 == len(timer_node_links), f'len={len(timer_node_links)}'
#     timer_handle = timer_node_links[0]

#     # Get creation timestamp
#     df = data_util.convert_time_columns(data_util.data.timers, [], ['timestamp'], False)
#     return df.loc[timer_handle, 'timestamp']


def get_timer_callback_ranges(timer_node_name: str) -> TimeRanges:
    """Get timer callback instance ranges."""
    # Get timer object
    objs_and_owners = {
        obj: data_util.get_callback_owner_info(obj)
        for obj, _ in callback_symbols.items()
    }
    timer_objs = [
        obj for obj, owner_info in objs_and_owners.items()
        if timer_node_name in owner_info and 'Timer' in owner_info
    ]
    assert 1 == len(timer_objs), f'len={len(timer_objs)}'
    timer_obj = timer_objs[0]
    print(f"Timer for node '{timer_node_name}': 0x{timer_obj:x}")

    # Get callback durations
    callback_durations = data_util.get_callback_durations(timer_obj)

    # Convert to simple list of tuples
    ranges = []
    for _, row in callback_durations.iterrows():
        begin = row['timestamp']
        duration = row['duration']
        ranges.append((begin, begin + duration, duration))
    return ranges


def get_sub_callback_ranges(
    sub_topic_name: str,
    node_name: Optional[str] = None,
) -> TimeRanges:
    """Get subscription callback instance ranges."""
    # Get callback object
    objs_and_owners = {
        obj: data_util.get_callback_owner_info(obj)
        for obj, _ in callback_symbols.items()
    }
    sub_objs = [
        obj for obj, owner_info in objs_and_owners.items()
        if sub_topic_name in owner_info
        and (node_name in owner_info if node_name is not None else True)
    ]
    assert 1 == len(sub_objs), f'len={len(sub_objs)}'
    sub_obj = sub_objs[0]

    # Get callback durations
    callback_durations = data_util.get_callback_durations(sub_obj)

    # Convert to simple list of tuples
    ranges = []
    for _, row in callback_durations.iterrows():
        begin = row['timestamp']
        duration = row['duration']
        ranges.append((begin, begin + duration, duration))
    return ranges


def get_sub_callback_times(
    sub_topic_name: str,
    node_name: Optional[str] = None,
) -> List[pd.Timestamp]:
    """Get subscription callback timestamps for topic and node."""
    ranges = get_sub_callback_ranges(sub_topic_name, node_name)
    return [r[0] for r in ranges]


def get_publish_times(pub_topic_name: str) -> List[pd.Timestamp]:
    """Get publication timestamps for topic."""
    # Get all publish instances
    pub_instances = data_util.get_publish_instances()

    # Get publisher handle
    pub_handle = get_handle('pub', pub_topic_name)

    # Since publish calls go rclcpp->rcl->rmw and since we
    # only know the publisher handle at the rcl level, we first
    # get the indexes of all rcl_publish calls for our publisher
    rcl_pub_indexes = pub_instances.loc[
        pub_instances['publisher_handle'] == pub_handle
    ].index.values.astype(int)
    rcl_pub_indexes = list(rcl_pub_indexes)
    max_index = pub_instances.index.values.astype(int).max()
    # Then we group rclcpp & rmw calls (before & after,
    # respectively) with matching message pointers
    rclcpp_rmw_pub_timestamps = []
    for rcl_pub_index in rcl_pub_indexes:
        # Get message pointer value
        message = pub_instances.iloc[rcl_pub_index]['message']
        # Get corresponding rclcpp_publish row
        rclcpp_timestamp = None
        rclcpp_pub_index = rcl_pub_index - 1
        while rclcpp_pub_index >= 0:
            # Find the first row above with the same message
            row = pub_instances.iloc[rclcpp_pub_index]
            if message == row['message'] and 'rclcpp' == row['layer']:
                rclcpp_timestamp = row['timestamp']
                break
            rclcpp_pub_index -= 1
        # Get corresponding rmw_publish row
        rmw_timestamp = None
        rmw_pub_index = rcl_pub_index + 1
        while rmw_pub_index <= max_index:
            # Find the first row below rcl_publish row with the same message
            row = pub_instances.iloc[rmw_pub_index]
            if message == row['message'] and 'rmw' == row['layer']:
                rmw_timestamp = row['timestamp']
                break
            rmw_pub_index += 1

        assert rclcpp_timestamp is not None and rmw_timestamp is not None
        rclcpp_rmw_pub_timestamps.append(rclcpp_timestamp + (rmw_timestamp - rclcpp_timestamp) / 2)

    return rclcpp_rmw_pub_timestamps


def get_intervals(ranges: TimeRanges) -> Tuple[List[float], List[float]]:
    """Compute time intervals between ranges."""
    times = []
    periods = []
    starttime = ranges[0][0]
    endtime = ranges[-1][1]
    for i in range(1, len(ranges)):
        times.append(
            float(pd.Timedelta.to_numpy(ranges[i][0] - starttime) / np.timedelta64(1, 's')))
        periods.append(
            float(
                pd.Timedelta.to_numpy(ranges[i][0] - ranges[i - 1][0]) / np.timedelta64(1, 'ms')))

    highest_interval_index = max(range(len(periods)), key=periods.__getitem__)
    highest_interval_value = periods[highest_interval_index]
    highest_interval_time = starttime + (np.timedelta64(1, 's') * times[highest_interval_index])
    print(f'Time intervals between: {starttime} - {endtime}')
    print(
        f'Highest timer callback interval of {highest_interval_value} ms at {highest_interval_time} '
        f'or {times[highest_interval_index]} s '
        f'(interval index={highest_interval_index}, callback index={highest_interval_index + 1})'
    )

    return times, periods


def get_begins_durations(ranges: TimeRanges) -> Tuple[List[float], List[float]]:
    """Split time ranges into relative begin ms timestamps list and duration list."""
    times = []
    durations = []
    starttime = ranges[0][0]
    for i in range(len(ranges)):
        times.append(
            float(pd.Timedelta.to_numpy(ranges[i][0] - starttime) / np.timedelta64(1, 's')))
        durations.append(float(pd.Timedelta.to_numpy(ranges[i][2]) / np.timedelta64(1, 'ms')))
    return times, durations


def plot_timer(
    ranges_timer: TimeRanges,
    title: str = 'Timer callback interval and duration over time',
    xlabel: str = 'time (s)',
    ylabel_interval: str = 'callback interval (ms)',
    ylabel_duration: str = 'callback duration (ms)',
    label_interval: str = 'period',
    label_duration: str = 'duration',
    marker: str = '.',
    color_interval: str = 'b',
    color_duration: str = 'r',
    name: str = '5_analysis_timer',
) -> None:
    """Plot timer callback interval and duration."""
    timer_period_x, timer_period_y = get_intervals(ranges_timer)
    timer_duration_x, timer_duration_y = get_begins_durations(ranges_timer)

    fig, (ax1, ax2) = plt.subplots(2, 1, constrained_layout=True)
    ax1.plot(timer_period_x, timer_period_y, marker + color_interval, label=label_interval)
    ax2.plot(timer_duration_x, timer_duration_y, marker + color_duration, label=label_duration)
    ax1.grid()
    ax2.grid()

    if include_plot_title:
        ax1.set_title(title)
    ax2.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel_interval)
    ax2.set_ylabel(ylabel_duration)
    ax1.set_xticklabels([])
    fig.align_ylabels()

    filename = f'{trace_name}/{name}'
    fig.savefig(f'{filename}.png')
    fig.savefig(f'{filename}.svg')
    fig.savefig(f'{filename}.pdf')


def to_relative_ms(
    times_lists: List[List[pd.Timestamp]],
    ranges_lists: List[TimeRanges],
    time_offset: float,
) -> None:
    """Transform timestamps to relative time in ms from beginning."""
    start = min(
        min(itertools.chain.from_iterable(times_lists)),
        min(ranges[0] for ranges_list in ranges_lists for ranges in ranges_list),
    )
    for times_list in times_lists:
        times_list[:] = [time_offset + ((time - start).total_seconds() * 1000.0) for time in times_list]
    for ranges_list in ranges_lists:
        ranges_list[:] = [
            (
                time_offset + ((ranges[0] - start).total_seconds() * 1000.0),
                time_offset + ((ranges[1] - start).total_seconds() * 1000.0),
                ranges[2].total_seconds() * 1000.0
            )
            for ranges in ranges_list
        ]


def add_markers_to_axis(
    ax: plt.Axes,
    label: str,
    times: List[Tuple[str, float]],
    marker: str = 'o',
    markersize: int = 8,
) -> None:
    """Add time markers to axis."""
    for color, time in times:
        ax.plot([time], [label], marker, color=color, markersize=markersize)


def add_ranges_to_axis(
    ax: plt.Axes,
    label: str,
    ranges: List[Tuple[str, Tuple[float, float, float]]],
    linewidth: int = 35,
) -> None:
    """Add start-end ranges to axis."""
    for color, r in ranges:
        ax.plot(
            [r[0], r[1]],
            [label, label],
            '-',
            color=color,
            linewidth=linewidth,
            solid_capstyle='butt',  # Prevent line width from affecting length of line
        )


def get_default_colors() -> List[str]:
    """Get the list of default matplotlib colours."""
    return [p['color'] for p in plt.rcParams['axes.prop_cycle']]


def plot_chart(
    times_sub_ObjectCollisionEstimator,
    times_sub_NDTLocalizer,
    times_sub_Lanelet2GlobalPlanner,
    times_sub_Lanelet2MapLoader,
    times_sub_ParkingPlanner,
    times_sub_LanePlanner,
    ranges_timer_BehaviorPlanner,
    times_pub_BehaviorPlanner,
    title: str = 'Message reception \& publication and timer execution',  # noqa: W605
    xlabel: str = 'time (ms)',
    name: str = '5_analysis_time_chart',
    num_instances: int = 5,
    time_offset: float = 6.0,  # Manual adjustment
) -> None:
    """Plot time chart with msg reception, msg publication, and timer callback instances."""
    to_relative_ms(
        [
            times_sub_ObjectCollisionEstimator,
            times_sub_NDTLocalizer,
            times_sub_Lanelet2GlobalPlanner,
            times_sub_Lanelet2MapLoader,
            times_sub_ParkingPlanner,
            times_sub_LanePlanner,
            times_pub_BehaviorPlanner,
        ],
        [
            ranges_timer_BehaviorPlanner,
        ],
        time_offset,
    )

    # Keep only the instances we want
    ranges_timer_BehaviorPlanner = ranges_timer_BehaviorPlanner[:num_instances]
    # Pub instances shoud closely follow timer ranges
    times_pub_BehaviorPlanner = times_pub_BehaviorPlanner[:num_instances]
    # Drop sub times after the last timer callback instance start time

    def filter_time(times: List[float], last_time: float) -> List[float]:
        return [time for time in times if time <= last_time]

    last_time = ranges_timer_BehaviorPlanner[len(ranges_timer_BehaviorPlanner) - 1][0]
    times_sub_ObjectCollisionEstimator = filter_time(times_sub_ObjectCollisionEstimator, last_time)
    times_sub_NDTLocalizer = filter_time(times_sub_NDTLocalizer, last_time)
    times_sub_Lanelet2GlobalPlanner = filter_time(times_sub_Lanelet2GlobalPlanner, last_time)
    times_sub_Lanelet2MapLoader = filter_time(times_sub_Lanelet2MapLoader, last_time)
    times_sub_ParkingPlanner = filter_time(times_sub_ParkingPlanner, last_time)
    times_sub_LanePlanner = filter_time(times_sub_LanePlanner, last_time)

    # Assign colours to link input messages to corresponding timer callback and output message
    colours = get_default_colors()[:len(ranges_timer_BehaviorPlanner)]
    deadlines = [r[0] for r in ranges_timer_BehaviorPlanner]
    ranges_timer_BehaviorPlanner = [
        (colours[i], ranges_timer_BehaviorPlanner[i])
        for i in range(len(ranges_timer_BehaviorPlanner))
    ]

    def get_colour(time: float, pre: bool) -> str:
        """
        Get colour string for given timestamp.

        :param time: the timestamp
        :param pre: whether the colour should correspond to the next deadline (True) or the previous one (False)
        """
        for i in range(len(deadlines)):
            deadline = deadlines[i]
            if pre:
                # Given time has to be before given deadline, but after previous deadline
                if (
                    (0 == i and time <= deadline)
                    or (i > 0 and time <= deadline and time > deadlines[i - 1])
                ):
                    return colours[i]
            else:
                # Given time has to be after given deadline, but before next deadline
                if (
                    (len(deadlines) - 1 == i and time >= deadline)
                    or (i < len(deadlines) - 1 and time >= deadline and time < deadlines[i + 1])
                ):
                    return colours[i]
        assert False, 'should have a matching colour'

    def with_colour(times: List[float], pre: bool) -> List[Tuple[str, float]]:
        return [(get_colour(times[i], pre), times[i]) for i in range(len(times))]

    times_pub_BehaviorPlanner = with_colour(times_pub_BehaviorPlanner, False)
    times_sub_LanePlanner = with_colour(times_sub_LanePlanner, True)
    times_sub_ParkingPlanner = with_colour(times_sub_ParkingPlanner, True)
    times_sub_Lanelet2MapLoader = with_colour(times_sub_Lanelet2MapLoader, True)
    times_sub_Lanelet2GlobalPlanner = with_colour(times_sub_Lanelet2GlobalPlanner, True)
    times_sub_NDTLocalizer = with_colour(times_sub_NDTLocalizer, True)
    times_sub_ObjectCollisionEstimator = with_colour(times_sub_ObjectCollisionEstimator, True)

    fig, ax = plt.subplots(1, 1, constrained_layout=True)

    # Order on Y axis: first->last == bottom->top
    add_markers_to_axis(ax, 'pub.', times_pub_BehaviorPlanner)
    add_ranges_to_axis(ax, 'timer', ranges_timer_BehaviorPlanner)
    add_markers_to_axis(ax, 'sub. 6', times_sub_LanePlanner)
    add_markers_to_axis(ax, 'sub. 5', times_sub_ParkingPlanner)
    add_markers_to_axis(ax, 'sub. 4', times_sub_Lanelet2MapLoader)
    add_markers_to_axis(ax, 'sub. 3', times_sub_Lanelet2GlobalPlanner)
    add_markers_to_axis(ax, 'sub. 2', times_sub_NDTLocalizer)
    add_markers_to_axis(ax, 'sub. 1', times_sub_ObjectCollisionEstimator)

    ax.grid()
    if include_plot_title:
        ax.set_title(title)
    ax.set_xlabel(xlabel)

    filename = f'{trace_name}/{name}'
    fig.savefig(f'{filename}.png')
    fig.savefig(f'{filename}.svg')
    fig.savefig(f'{filename}.pdf')


def main(argv=sys.argv[1:]) -> int:
    """Plot analyss results for given trace."""
    if len(argv) != 1:
        print('error: must provide only 1 argument: name of directory containing trace')
        return 1
    global trace_name
    trace_name = argv[0].strip('/')
    print(f'Trace directory: {trace_name}')

    # Process
    path = f'{trace_name}/ust'
    events = load_file(path)
    handler = Ros2Handler.process(events)
    global data_util
    data_util = Ros2DataModelUtil(handler.data)
    global callback_symbols
    callback_symbols = data_util.get_callback_symbols()
    # data_util.data.print_data()

    # Analyze
    # The BehaviorPlanner node is a cyclic type node with 6 input topics, 1 periodic callback, and 1 output topic
    # See: https://github.com/ros-realtime/reference-system/blob/6baa1d0d0061ad901cc08e559d8e6acdb169c18b/autoware_reference_system/include/autoware_reference_system/autoware_system_builder.hpp#L193-L203  # noqa: E501
    times_sub_ObjectCollisionEstimator = get_sub_callback_times('/ObjectCollisionEstimator', 'BehaviorPlanner')
    times_sub_NDTLocalizer = get_sub_callback_times('/NDTLocalizer', 'BehaviorPlanner')
    times_sub_Lanelet2GlobalPlanner = get_sub_callback_times('/Lanelet2GlobalPlanner', 'BehaviorPlanner')
    times_sub_Lanelet2MapLoader = get_sub_callback_times('/Lanelet2MapLoader', 'BehaviorPlanner')
    times_sub_ParkingPlanner = get_sub_callback_times('/ParkingPlanner', 'BehaviorPlanner')
    times_sub_LanePlanner = get_sub_callback_times('/LanePlanner', 'BehaviorPlanner')
    ranges_timer_BehaviorPlanner = get_timer_callback_ranges('BehaviorPlanner')
    times_pub_BehaviorPlanner = get_publish_times('/BehaviorPlanner')

    # Plot
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif', size=14)
    plt.rc('axes', titlesize=20)

    # Plot BehaviorPlanner timer period and callback duration
    plot_timer(ranges_timer_BehaviorPlanner)

    # Plot pub/sub/timer time chart
    plot_chart(
        times_sub_ObjectCollisionEstimator,
        times_sub_NDTLocalizer,
        times_sub_Lanelet2GlobalPlanner,
        times_sub_Lanelet2MapLoader,
        times_sub_ParkingPlanner,
        times_sub_LanePlanner,
        ranges_timer_BehaviorPlanner,
        times_pub_BehaviorPlanner,
    )

    plt.show()

    return 0


if __name__ == '__main__':
    sys.exit(main())
