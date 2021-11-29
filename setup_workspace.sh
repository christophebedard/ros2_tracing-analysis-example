#!/usr/bin/env bash
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

analysis_ws="analysis_ws"

mkdir -p ${analysis_ws}/src
cd ${analysis_ws}
# TODO use release/tag
vcs import src --input https://raw.githubusercontent.com/ros2/ros2/master/ros2.repos
cd src/
git clone https://github.com/ros-realtime/reference-system.git
git clone https://gitlab.com/ros-tracing/tracetools_analysis.git
cd ../
colcon build --packages-up-to autoware_reference_system ros2run ros2launch --mixin release --cmake-args -DRUN_BENCHMARK=TRUE -DTEST_PLATFORM=FALSE
