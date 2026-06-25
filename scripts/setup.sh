#!/usr/bin/env bash
# ONE-TIME host build (Ubuntu 22.04). Clones + builds PX4 v1.14.3 SITL and the Micro-XRCE
# agent into /home using the host toolchain (no sudo). Pegasus + Isaac run in the container
# (separate step: scripts/setup_container.sh). Idempotent: safe to re-run to resume.
#
# Run in the background so an SSH drop doesn't kill the long PX4 build:
#   nohup bash ~/isaac-bringup/scripts/setup.sh > ~/setup.log 2>&1 &
#   grep STAGE ~/setup.log          # watch progress
set -eo pipefail

WS="$HOME/droneranger-isaac"
mkdir -p "$WS"
cd "$WS"

clone() { [ -d "$2/.git" ] || git clone "$1" "$2"; }

echo "STAGE 1: clone repos -> $WS"
clone https://github.com/PX4/PX4-Autopilot.git PX4-Autopilot
clone https://github.com/eProsima/Micro-XRCE-DDS-Agent.git Micro-XRCE-DDS-Agent
clone https://github.com/PegasusSimulator/PegasusSimulator.git PegasusSimulator
clone https://github.com/RipZou/DroneRangerIssac.git DroneRangerIssac
( cd PX4-Autopilot && git checkout v1.14.3 && git submodule update --init --recursive )
( cd Micro-XRCE-DDS-Agent && git checkout v2.4.2 )
( cd PegasusSimulator && git checkout v5.1.0 )

echo "STAGE 2: PX4 python deps (user site, no sudo)"
python3 -m pip install --user --upgrade pip >/dev/null 2>&1 || true
python3 -m pip install --user -r PX4-Autopilot/Tools/setup/requirements.txt

echo "STAGE 3: XRCE Fast-DDS tag fix (deleted upstream branch 2.12.x -> v2.12.2)"
XC="Micro-XRCE-DDS-Agent/CMakeLists.txt"
if grep -q "2.12.x" "$XC"; then sed -i 's/2\.12\.x/v2.12.2/' "$XC"; echo "  patched"; else echo "  no patch needed"; fi

echo "STAGE 4: build Micro-XRCE-DDS agent"
( cd Micro-XRCE-DDS-Agent && mkdir -p build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j"$(nproc)" )
echo "  XRCE binary: $(ls -1 "$WS"/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent 2>/dev/null || echo MISSING)"

echo "STAGE 5: build PX4 SITL (SLOW, ~20-40 min)"
( cd PX4-Autopilot && make px4_sitl_default )
echo "  PX4 binary: $(ls -1 "$WS"/PX4-Autopilot/build/px4_sitl_default/bin/px4 2>/dev/null || echo MISSING)"

echo "STAGE 6: disk check"
df -h "$HOME" | tail -1

echo "SETUP HOST BUILD COMPLETE"
