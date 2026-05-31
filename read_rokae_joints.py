#!/usr/bin/env python3
"""Read current joint angles from the ROKAE robot controllers.

This script is intentionally read-only: it connects through the ROKAE SDK and
calls jointPos(), without switching operation mode, powering on, or starting RT
control.
"""

from __future__ import annotations

import argparse
import json
import math
import socket
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from rokae_python_wrapper.rokae_sdk import xCoreSDK_python as rokae_sdk_api


@dataclass(frozen=True)
class RobotTarget:
    name: str
    ip: str
    sdk_classes: tuple[str, ...]
    joint_labels: tuple[str, ...]


DEFAULT_TARGETS: tuple[RobotTarget, ...] = (
    RobotTarget(
        name="right_arm",
        ip="192.168.71.160",
        sdk_classes=("xMateErProRobot",),
        joint_labels=("J1", "J2", "J3", "J4", "J5", "J6", "J7"),
    ),
    RobotTarget(
        name="left_arm",
        ip="192.168.71.161",
        sdk_classes=("xMateErProRobot",),
        joint_labels=("J1", "J2", "J3", "J4", "J5", "J6", "J7"),
    ),
    RobotTarget(
        name="taihu",
        ip="192.168.71.254",
        # TaiHu appears as a 4-axis body controller in Robot Assist. Try both
        # public 4-axis SDK wrappers because deployments differ in class names.
        sdk_classes=("Robot_T_Industrial_4", "IndustrialRobot_4"),
        joint_labels=("J1", "J2", "J3", "J4"),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read current joint angles from right arm, left arm, and TaiHu.",
    )
    parser.add_argument(
        "--host-ip",
        default="192.168.71.56",
        help="Local PC IP on the robot subnet. Default: %(default)s",
    )
    parser.add_argument(
        "--target",
        choices=[target.name for target in DEFAULT_TARGETS] + ["all"],
        default="all",
        help="Target controller to read. Default: %(default)s",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a human table.",
    )
    parser.add_argument(
        "--check-port",
        action="store_true",
        help="Check TCP/5050 reachability before SDK connection.",
    )
    return parser.parse_args()


def enum_name(value: Any) -> str:
    return getattr(value, "name", str(value))


def ec_summary(ec: dict[str, Any]) -> dict[str, Any] | None:
    return ec.copy() if ec else None


def tcp_reachable(ip: str, port: int = 5050, timeout_s: float = 0.7) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def make_robot(class_name: str, ip: str, host_ip: str) -> Any:
    cls: Callable[..., Any] = getattr(rokae_sdk_api, class_name)
    return cls(ip, host_ip)


def read_target(target: RobotTarget, host_ip: str, check_port: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": target.name,
        "ip": target.ip,
        "ok": False,
        "sdk_class": None,
        "joint_labels": list(target.joint_labels),
    }

    if check_port and not tcp_reachable(target.ip):
        result["error"] = "tcp/5050 not reachable"
        return result

    errors: list[str] = []
    for class_name in target.sdk_classes:
        ec: dict[str, Any] = {}
        try:
            robot = make_robot(class_name, target.ip, host_ip)
            joint_rad = [float(x) for x in robot.jointPos(ec)]
            joint_deg = [math.degrees(x) for x in joint_rad]

            result.update(
                {
                    "ok": True,
                    "sdk_class": class_name,
                    "joint_rad": joint_rad,
                    "joint_deg": joint_deg,
                    "ec": ec_summary(ec),
                }
            )

            for attr_name, method_name in (
                ("power_state", "powerState"),
                ("operate_mode", "operateMode"),
                ("operation_state", "operationState"),
            ):
                state_ec: dict[str, Any] = {}
                try:
                    state = getattr(robot, method_name)(state_ec)
                    result[attr_name] = enum_name(state)
                    if state_ec:
                        result[f"{attr_name}_ec"] = state_ec.copy()
                except Exception as exc:  # State reads are helpful but optional.
                    result[f"{attr_name}_error"] = str(exc)

            return result
        except Exception as exc:
            errors.append(f"{class_name}: {exc}")

    result["error"] = "; ".join(errors)
    return result


def print_human(results: list[dict[str, Any]]) -> None:
    print(f"ROKAE joint snapshot @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    for item in results:
        title = f"{item['name']} ({item['ip']})"
        print(title)
        print("-" * len(title))
        if not item.get("ok"):
            print(f"ERROR: {item.get('error', 'unknown error')}")
            print()
            continue

        print(f"sdk_class: {item['sdk_class']}")
        if "power_state" in item:
            print(f"state: power={item.get('power_state')} operate={item.get('operate_mode')} operation={item.get('operation_state')}")

        labels = item.get("joint_labels") or []
        deg = item["joint_deg"]
        rad = item["joint_rad"]
        for idx, (rad_value, deg_value) in enumerate(zip(rad, deg, strict=False), start=1):
            label = labels[idx - 1] if idx - 1 < len(labels) else f"J{idx}"
            print(f"  {label}: {deg_value:9.3f} deg   {rad_value: .6f} rad")

        if item.get("ec"):
            print(f"ec: {item['ec']}")
        print()


def main() -> int:
    args = parse_args()
    targets = (
        list(DEFAULT_TARGETS)
        if args.target == "all"
        else [target for target in DEFAULT_TARGETS if target.name == args.target]
    )
    results = [read_target(target, args.host_ip, args.check_port) for target in targets]

    if args.json:
        print(json.dumps({"host_ip": args.host_ip, "results": results}, indent=2, ensure_ascii=False))
    else:
        print_human(results)

    return 0 if all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    sys.exit(main())
