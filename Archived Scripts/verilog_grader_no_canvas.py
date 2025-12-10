#!/usr/bin/env python3
"""
Auto-grade a Verilog lab using Icarus Verilog.

Assumptions:
- You provide a testbench TB that instantiates the student's DUT.
- The testbench prints lines like:
    RESULT: test_name PASS
    RESULT: test_name FAIL expected=... got=...
- This script compiles and runs the sim, parses those lines,
  and prints a summary with a numeric score.
"""

import argparse
import os
import subprocess
import sys
import tempfile
import re

def run_cmd(cmd, cwd=None):
    print(">>", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("STDOUT:\n", proc.stdout)
        print("STDERR:\n", proc.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return proc.stdout, proc.stderr

def grade_verilog(dut_files, tb_file, top_module="tb_top"):
    # Convert all paths to absolute so they work from any CWD
    dut_files_abs = [os.path.abspath(p) for p in dut_files]
    tb_file_abs = os.path.abspath(tb_file)

    with tempfile.TemporaryDirectory() as builddir:
        vvp_out = os.path.join(builddir, "sim.out")

        # 1) Compile with iverilog
        cmd_compile = [
            "iverilog",
            "-o", vvp_out,
            "-s", top_module,
        ]
        cmd_compile.extend(dut_files_abs)
        cmd_compile.append(tb_file_abs)

        stdout, stderr = run_cmd(cmd_compile, cwd=builddir)

        # 2) Run the simulation
        sim_stdout, sim_stderr = run_cmd(["vvp", vvp_out], cwd=builddir)

        # 3) Parse RESULT lines (same as before)
        results = []
        for line in sim_stdout.splitlines():
            if line.startswith("RESULT:"):
                results.append(line.strip())

        if not results:
            print("No RESULT lines found. Did the testbench run correctly?")
            print("Simulator output:\n", sim_stdout)
            return 0.0

        total = 0
        passed = 0
        for r in results:
            total += 1
            if "PASS" in r.split():
                passed += 1

        score = passed / total * 100.0

        print("---- Detailed Results ----")
        for r in results:
            print(r)
        print("--------------------------")
        print(f"Score: {passed}/{total} = {score:.1f}%")

        return score

    # Convert all paths to absolute so they work from any CWD
    dut_files_abs = [os.path.abspath(p) for p in dut_files]
    tb_file_abs = os.path.abspath(tb_file)

    with tempfile.TemporaryDirectory() as builddir:
        vvp_out = os.path.join(builddir, "sim.out")

        # 1) Compile with iverilog
        cmd_compile = [
            "iverilog",
            "-o", vvp_out,
            "-s", top_module,
        ]
        cmd_compile.extend(dut_files_abs)
        cmd_compile.append(tb_file_abs)

        stdout, stderr = run_cmd(cmd_compile, cwd=builddir)

        # 2) Run the simulation
        sim_stdout, sim_stderr = run_cmd(["vvp", vvp_out], cwd=builddir)

        # 3) Parse RESULT lines (same as before)
        results = []
        for line in sim_stdout.splitlines():
            if line.startswith("RESULT:"):
                results.append(line.strip())

        if not results:
            print("No RESULT lines found. Did the testbench run correctly?")
            print("Simulator output:\n", sim_stdout)
            return 0.0

        total = 0
        passed = 0
        for r in results:
            total += 1
            if "PASS" in r.split():
                passed += 1

        score = passed / total * 100.0

        print("---- Detailed Results ----")
        for r in results:
            print(r)
        print("--------------------------")
        print(f"Score: {passed}/{total} = {score:.1f}%")

        return score

def main():
    parser = argparse.ArgumentParser(description="Auto-grade Verilog lab with Icarus Verilog")
    parser.add_argument("--dut", nargs="+", required=True,
                        help="Path(s) to student DUT .v file(s).")
    parser.add_argument("--tb", required=True,
                        help="Path to instructor-provided testbench .v file.")
    parser.add_argument("--top", default="tb_top",
                        help="Top-level testbench module name.")

    args = parser.parse_args()

    try:
        score = grade_verilog(args.dut, args.tb, top_module=args.top)
    except Exception as e:
        print(f"ERROR during grading: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
