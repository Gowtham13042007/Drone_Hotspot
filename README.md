# Drone_Hotspot_Landing 🚁

A ROS 2 autonomous drone inspection package that uses PX4 + MAVROS to navigate a drone through predefined hotspot locations for automated site inspection in a Gazebo Classic simulation environment.

---

## Overview

`drone_hotspot` commands a PX4-powered drone to autonomously take off, visit a sequence of inspection hotspots (industrial tank, electrical substation, and cell tower), perform a descent inspection at each one, and return home — all without manual input.

The package includes:
- A **ROS 2 Python controller node** (`DroneController`) that interfaces with PX4 via MAVROS in OFFBOARD mode
- A **Gazebo Classic SDF world** (`drone_inspection_world`) with realistic inspection targets and environment

---

## Package Structure

```
Drone_Hotspot/
├── drone_hotspot/
│   └── drone_controller.py         # Main ROS 2 controller node
├── worlds/
│   └── drone_inspection_world.sdf  # Gazebo Classic simulation world
├── resource/
├── test/
├── package.xml
├── setup.cfg
└── setup.py
```

---

## Prerequisites

| Dependency | Version |
|---|---|
| ROS 2 | Humble / Iron |
| PX4 Autopilot | v1.13 / v1.14 |
| MAVROS | ≥ 2.x |
| Gazebo Classic | 11 (gazebo11) |
| Python | ≥ 3.8 |

### Install Gazebo Classic

```bash
sudo apt install gazebo libgazebo-dev ros-$ROS_DISTRO-gazebo-ros-pkgs
```

### Install PX4

```bash
git clone https://github.com/PX4/PX4-Autopilot.git --recursive
cd PX4-Autopilot
bash ./Tools/setup/ubuntu.sh
```

### Install MAVROS

```bash
sudo apt install ros-$ROS_DISTRO-mavros ros-$ROS_DISTRO-mavros-extras ros-$ROS_DISTRO-mavros-msgs
wget https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh
sudo bash install_geographiclib_datasets.sh
```

---

## Installation

```bash
# Clone into your ROS 2 workspace
cd ~/ros2_ws/src
git clone https://github.com/Gowtham13042007/Drone_Hotspot.git

# Install dependencies
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y

# Build
colcon build --packages-select drone_hotspot

# Source
source install/setup.bash
```

---

## Running the Simulation

Run each of the following in a **separate terminal**. Source your workspace in each one.

### Terminal 1 — Launch PX4 SITL with Gazebo Classic

PX4 launches Gazebo Classic internally using `make px4_sitl_default`. This starts both the PX4 SITL firmware and Gazebo Classic together — no separate `gazebo` command is needed.

```bash
cd ~/PX4-Autopilot
make px4_sitl_default gazebo
```

**To use the custom inspection world**, pass the world file path directly via the `PX4_SITL_WORLD` variable — no `GAZEBO_MODEL_PATH` or any other export required:

```bash
cd ~/PX4-Autopilot
PX4_SITL_WORLD=/absolute/path/to/drone_inspection_world.sdf make px4_sitl_default gazebo
```

> Gazebo Classic loads the SDF directly from the absolute path, bypassing any world search path lookup entirely.

---

### Terminal 2 — Launch MAVROS

Connect MAVROS to the PX4 SITL instance. PX4 SITL listens on UDP port `14540` by default.

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
ros2 run mavros mavros_node --ros-args \
  -p fcu_url:=udp://:14540@127.0.0.1:14557 \
  -p gcs_url:=udp://@127.0.0.1:14550
```

Verify the connection is alive:
```bash
ros2 topic echo /mavros/state
```
You should see `connected: True` and `mode: MANUAL` before proceeding to Terminal 3.

---

### Terminal 3 — Run the Drone Controller

```bash
source ~/ros2_ws/install/setup.bash
ros2 run drone_hotspot drone_controller
```

The controller will:
1. Pre-publish 100 setpoints (~5 s) to prime the OFFBOARD heartbeat
2. Switch PX4 to **OFFBOARD** mode
3. **Arm** the drone
4. Execute the full inspection mission
5. **Disarm** and return to **MANUAL** mode

---

## PX4 OFFBOARD Mode — How It Works

PX4 will only enter and stay in OFFBOARD mode if it receives a continuous stream of setpoints at **≥ 2 Hz**. The controller publishes at **20 Hz** via `/mavros/setpoint_position/local` to comfortably satisfy this requirement.

```
PX4 SITL  ←——UDP 14540——→  MAVROS  ←——ROS 2 topics——→  DroneController
                                    /mavros/setpoint_position/local  (publish)
                                    /mavros/cmd/arming               (service)
                                    /mavros/set_mode                 (service)
```

If the setpoint stream is interrupted for more than 0.5 s, PX4 will automatically exit OFFBOARD mode and the mission will abort.

---

## Mission Profile

```
[Home (0, 0)]
     │
     ▼  Takeoff to 5 m
     │
     ▼  Fly to Hotspot 1 → (2, -1)  [Industrial Tank]
     │     └─ Descend to ground → Inspect → Climb back to 5 m
     │
     ▼  Fly to Hotspot 2 → (0, 4)   [Electrical Substation]
     │     └─ Descend to ground → Inspect → Climb back to 5 m
     │
     ▼  Fly to Hotspot 3 → (5, 1)   [Cell Tower / Antenna Mast]
     │     └─ Descend to ground → Inspect → Climb back to 5 m
     │
     ▼  Return to Home (0, 0)
     │
     ▼  Land → Disarm → MANUAL mode
```

---

## Simulation World — Hotspots

| Hotspot | Coordinates | Object |
|---|---|---|
| 1 | (2.0, -1.0) | Industrial storage tank with warning stripe |
| 2 | (0.0, 4.0)  | Electrical substation / transformer box |
| 3 | (5.0, 1.0)  | Cell tower / antenna mast with aviation light |

The world also features a textured grass ground plane, perimeter fencing, scattered trees and boulders, directional sun + ambient lighting, atmospheric fog, and a launch pad with an **H** marking at the origin.

---

## Key Parameters

| Parameter | Value | Description |
|---|---|---|
| `base_alt` | 5.0 m | Cruise altitude between waypoints |
| `duration_steps` | 200 | Interpolation steps per move segment |
| Step interval | 0.05 s | Sleep between steps (~20 Hz) |
| Publisher rate | 20 Hz | Setpoint publish rate (PX4 minimum: 2 Hz) |
| Flight mode | OFFBOARD | PX4 autonomous control mode |
| FCU URL | `udp://:14540@127.0.0.1:14557` | PX4 SITL default UDP port |

---

## Troubleshooting

**`connected: False` in `/mavros/state`**
PX4 SITL is not running or the UDP port is wrong. Confirm `make px4_sitl_default gazebo` completed successfully and that Gazebo Classic opened before starting MAVROS.

**Gazebo Classic window doesn't open**
Make sure `gazebo11` is installed and `GAZEBO_PLUGIN_PATH` is set by sourcing the Gazebo setup file:
```bash
source /usr/share/gazebo/setup.sh
```

**Drone won't enter OFFBOARD mode**
The setpoint stream must be active before calling `set_mode`. The controller pre-publishes 100 setpoints at startup to handle this. If it still fails, check that MAVROS shows `connected: True` first.

**Drone disarms immediately after arming**
PX4 may have a pre-arm check failure (e.g. no GPS fix in SITL). Disable the check via the PX4 shell (nsh prompt in Terminal 1):
```bash
param set COM_ARM_WO_GPS 1
```

**Build errors**
Ensure your workspace is sourced and all dependencies are installed:
```bash
rosdep install --from-paths src --ignore-src -r -y
```

---

