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

import os

import launch
import launch_ros
from tracetools_launch.action import Trace


def generate_launch_description():
    length_arg = launch.actions.DeclareLaunchArgument(
        'length',
        default_value='30.0',
        description='length of execution in seconds',
    )

    return launch.LaunchDescription([
        length_arg,
        Trace(
            session_name='system',
            append_timestamp=True,
            base_path=os.path.dirname(os.path.realpath(__file__)),
            events_ust=[
                'ros2:*',
            ],
            events_kernel=[
                'sched_switch',
                'sched_waking',
                'sched_pi_setprio',
                'sched_process_fork',
                'sched_process_exit',
                'sched_process_free',
                'sched_wakeup',
                'irq_softirq_entry',
                'irq_softirq_raise',
                'irq_softirq_exit',
                'irq_handler_entry',
                'irq_handler_exit',
                'lttng_statedump_process_state',
                'lttng_statedump_start',
                'lttng_statedump_end',
                'lttng_statedump_network_interface',
                'lttng_statedump_block_device',
                'block_rq_complete',
                'block_rq_insert',
                'block_rq_issue',
                'block_bio_frontmerge',
                'sched_migrate',
                'sched_migrate_task',
                'power_cpu_frequency',
                'net_dev_queue',
                'netif_receive_skb',
                'net_if_receive_skb',
                'timer_hrtimer_start',
                'timer_hrtimer_cancel',
                'timer_hrtimer_expire_entry',
                'timer_hrtimer_expire_exit',
            ],
        ),
        launch_ros.actions.Node(
            package='autoware_reference_system',
            executable='autoware_default_multithreaded',
        ),
        # Shut down after some time, otherwise the system would run indefinitely
        launch.actions.TimerAction(
            period=launch.substitutions.LaunchConfiguration(length_arg.name),
            actions=[launch.actions.Shutdown(reason='stopping system')],
        ),
    ])
