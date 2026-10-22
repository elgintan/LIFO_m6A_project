"""Measure a benchmark command and its descendants; run in the main environment.

Logs and exact local paths belong in ignored output directories. CPU is a
sampled lower bound, not an exact OS accounting total for short-lived workers.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-seconds", type=float, default=3600)
    parser.add_argument("--max-rss-mib", type=float, default=4096)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.max_seconds <= 0 or args.max_rss_mib <= 0:
        parser.error("A command and positive resource limits are required")
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        parser.error("Measurement directory must be empty; preserve earlier runs")
    began = time.perf_counter()
    cpu_by_pid, peak_tree, peak_parent, errors = {}, 0, 0, 0
    receipt = {"status": "running", "command": command, "cwd": os.getcwd(),
               "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "sampling_interval_seconds": .2,
               "cpu_scope": "maximum observed user+system CPU per command-tree PID; sampled lower bound",
               "rss_scope": "maximum sampled simultaneous sum of command-tree RSS; excludes monitor",
               "limits": {"wall_seconds": args.max_seconds, "tree_rss_mib": args.max_rss_mib}}
    path = args.output / "measurement.json"

    def save():
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        os.replace(str(temporary), str(path))

    process = None
    try:
        with (args.output / "stdout.log").open("wb") as stdout, (args.output / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, shell=False)
            receipt["pid"] = process.pid
            save()
            root = psutil.Process(process.pid)
            while process.poll() is None:
                try:
                    members = [root] + root.children(recursive=True)
                    total = 0
                    for member in members:
                        try:
                            rss = member.memory_info().rss
                            times = member.cpu_times()
                            cpu_by_pid[member.pid] = max(cpu_by_pid.get(member.pid, 0), times.user + times.system)
                            total += rss
                            if member.pid == root.pid:
                                peak_parent = max(peak_parent, rss)
                        except psutil.Error:
                            errors += 1
                    peak_tree = max(peak_tree, total)
                    if total > args.max_rss_mib * 1024**2:
                        raise RuntimeError("Measured command-tree memory limit reached")
                except psutil.NoSuchProcess:
                    pass
                if time.perf_counter() - began > args.max_seconds:
                    raise RuntimeError("Measured command wall-time limit reached")
                time.sleep(.2)
            receipt.update(status="complete" if process.returncode == 0 else "failed",
                           exit_code=process.returncode)
    except BaseException as error:
        receipt.update(status="interrupted_or_resource_failure", error=type(error).__name__ + ": " + str(error), exit_code=130 if isinstance(error, KeyboardInterrupt) else 1)
        if process is not None and process.poll() is None:
            try:
                owned = psutil.Process(process.pid)
                children = owned.children(recursive=True)
                for member in reversed(children):
                    try:
                        member.terminate()
                    except psutil.NoSuchProcess:
                        pass
                owned.terminate()
                psutil.wait_procs(children + [owned], timeout=5)
            except psutil.NoSuchProcess:
                pass
    finally:
        receipt.update(wall_seconds=time.perf_counter() - began,
                       sampled_process_tree_cpu_seconds_lower_bound=sum(cpu_by_pid.values()),
                       sampled_peak_tree_rss_mib=peak_tree / 1024**2,
                       sampled_peak_parent_rss_mib=peak_parent / 1024**2,
                       observed_processes=len(cpu_by_pid), sampling_errors=errors)
        save()
    print(json.dumps(receipt, indent=2), flush=True)
    return receipt["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
