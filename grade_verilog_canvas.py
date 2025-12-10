#!/usr/bin/env python3
"""
Grade Verilog assignments from Canvas using Icarus Verilog.

- User provides a comma-separated list of assignment IDs.
- For each assignment ID, this script:
  - Looks up that assignment in Canvas
  - Loads a local Verilog testbench named: testbenches/tb_<assignment_id>.v
    with top module: tb_<assignment_id>
  - For each student submission:
      * Downloads all .v attachments into a build folder
      * Compiles DUT(s) + testbench with iverilog
      * Runs vvp and parses RESULT: lines
      * Computes a numeric score (fraction of tests passed * points_possible)
      * Posts grade + comment back to Canvas

Requires:
- canvas_api.py in the same directory.
- config.txt with CANVAS_API_KEY, BASE_URL, COURSE_ID.
- Icarus Verilog (iverilog, vvp) installed and on PATH.
"""

import argparse
import os
import tempfile
import subprocess
import sys
import re
import requests

from canvas_api import (
    get_canvas_user_dict,
    get_student_submission,
    get_published_assignments_with_online_upload,
    post_grade_to_canvas,
    post_submission_comment,
)

# ---------------------------------------------------------------------------
# Config loading (same style as main.py)
# ---------------------------------------------------------------------------
def load_config(filename):
    """
    Reads a config file formatted with lines like:
    KEY = value
    and returns a dictionary of key/value pairs.
    """
    config = {}
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                config[key] = value
    return config

# ---------------------------------------------------------------------------
# Utility: run a shell command and capture output
# ---------------------------------------------------------------------------
def run_cmd(cmd, cwd=None):
    print(">>", " ".join(cmd))
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True
    )
    if proc.returncode != 0:
        print("STDOUT:\n", proc.stdout)
        print("STDERR:\n", proc.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return proc.stdout, proc.stderr

# ---------------------------------------------------------------------------
# Download student's Verilog attachments to a local directory
# ---------------------------------------------------------------------------
def download_verilog_attachments(submission_json, dest_dir, filename_prefix="dut"):
    """
    Given a Canvas submission JSON, download all .v attachments
    into dest_dir and return a list of local filenames (not full paths).
    """
    os.makedirs(dest_dir, exist_ok=True)
    dut_files = []

    attachments = submission_json.get("attachments", [])
    if not attachments:
        return dut_files

    idx = 0
    for att in attachments:
        url = att.get("url")
        display_name = att.get("display_name") or f"file_{idx}.v"
        if not url:
            continue

        if not display_name.lower().endswith(".v"):
            continue

        resp = requests.get(url)
        resp.raise_for_status()

        local_name = f"{filename_prefix}_{idx}_{display_name}"
        local_path = os.path.join(dest_dir, local_name)

        with open(local_path, "w", encoding="utf-8") as f:
            f.write(resp.text)

        # Return only the filename; we'll run iverilog with cwd=dest_dir
        dut_files.append(local_name)
        idx += 1

    return dut_files

# ---------------------------------------------------------------------------
# Grade a single submission using Icarus Verilog and a given testbench
# ---------------------------------------------------------------------------
def grade_submission_with_iverilog(
    assignment_id,
    points_possible,
    submission_json,
    testbench_path,
    top_module=None,
):
    """
    Compile and run the student's Verilog submission with the given testbench.

    If top_module is None, we do NOT pass -s to iverilog, and let Icarus infer
    the top-level module from the design (the testbench should be the root).
    """
    if submission_json is None:
        return 0.0, "No submission found."

    # Make a per-student build directory
    sis_id = submission_json.get("user_id", "unknown_user")
    build_dir = os.path.join(BUILD_ROOT, f"a{assignment_id}_u{sis_id}")
    os.makedirs(build_dir, exist_ok=True)

    # 1) Download DUT files
    dut_files = download_verilog_attachments(submission_json, build_dir, "dut")
    if not dut_files:
        return 0.0, "No Verilog (.v) attachments found in submission."

    if not os.path.isfile(testbench_path):
        return 0.0, f"Testbench not found on server: {testbench_path}"

    # 2) Compile with iverilog
    sim_out = os.path.join(build_dir, "sim.out")
    cmd_compile = ["iverilog", "-o", sim_out]

    if top_module:
        cmd_compile.extend(["-s", top_module])

    cmd_compile.extend(dut_files)                  # relative names
    cmd_compile.append(os.path.abspath(testbench_path))  # absolute

    try:
        stdout_compile, stderr_compile = run_cmd(cmd_compile, cwd=build_dir)
    except Exception as e:
        comment = f"Compilation failed:\n{str(e)}"
        return 0.0, comment


    # 3) Run the simulation
    try:
        sim_stdout, sim_stderr = run_cmd(["vvp", sim_out], cwd=build_dir)
    except Exception as e:
        comment = f"Simulation failed:\n{str(e)}"
        return 0.0, comment

    # 4) Parse RESULT lines
    results = []
    for line in sim_stdout.splitlines():
        if line.startswith("RESULT:"):
            results.append(line.strip())

    if not results:
        # No structured results; include raw stdout to help debug
        comment = (
            "No RESULT lines found in simulation output.\n\n"
            "Raw simulation output:\n"
            + sim_stdout
        )
        return 0.0, comment

    total = 0
    passed = 0
    details_lines = []
    for r in results:
        total += 1
        details_lines.append(r)
        if re.search(r"\bPASS\b", r):
            passed += 1

    fraction = passed / total if total > 0 else 0.0
    score = fraction * float(points_possible)

    comment = (
        f"Autograded Verilog assignment.\n"
        f"Tests passed: {passed}/{total} ({fraction*100:.1f}%).\n"
        f"Score: {score:.2f} / {points_possible}.\n\n"
        "Details:\n" + "\n".join(details_lines)
    )

    return score, comment

# ---------------------------------------------------------------------------
# Canvas integration for a set of assignment IDs
# ---------------------------------------------------------------------------
def get_assignments_by_id(base_url, course_id, api_key, assignment_ids):
    """
    Reuse get_published_assignments_with_online_upload and filter by ID.
    Returns a dict: id -> assignment_json
    """
    all_assignments = get_published_assignments_with_online_upload(
        base_url, course_id, api_key
    )
    by_id = {a["id"]: a for a in all_assignments}
    return {aid: by_id[aid] for aid in assignment_ids if aid in by_id}

def get_testbench_for_assignment(assignment_id):
    """
    Look for a folder named after the assignment ID inside TESTBENCH_DIR.

    Example: for assignment_id = 12345, we look in:
        testbenches/12345/

    Behavior:
    - If the folder does not exist:
        * Create it
        * Print a message and return None (nothing to grade yet)
    - If the folder exists:
        * Collect all .v files in that folder
        * If none:
            - Print an error and return None
        * If one or more:
            - Sort them and return the first one
    """
    tb_dir = os.path.join(TESTBENCH_DIR, str(assignment_id))

    if not os.path.isdir(tb_dir):
        os.makedirs(tb_dir, exist_ok=True)
        print(
            f"Created testbench directory for assignment {assignment_id}: {tb_dir}\n"
            f"Please add a Verilog testbench (.v) file to this folder. Skipping for now."
        )
        return None

    # Find all .v files in the directory
    entries = [
        f for f in os.listdir(tb_dir)
        if os.path.isfile(os.path.join(tb_dir, f)) and f.lower().endswith(".v")
    ]

    if not entries:
        print(
            f"No .v testbench files found in {tb_dir} for assignment {assignment_id}. "
            "Skipping this assignment."
        )
        return None

    entries.sort()
    chosen = entries[0]
    tb_path = os.path.join(tb_dir, chosen)
    print(f"Using testbench file for assignment {assignment_id}: {tb_path}")
    return tb_path

def main():
    parser = argparse.ArgumentParser(
        description="Grade Verilog Canvas assignments using Icarus Verilog."
    )
    parser.add_argument(
        "--assignments",
        help=(
            "Optional comma-separated list of Canvas assignment IDs to grade, "
            "e.g. 12345,23456. If omitted, uses VERILOG_ASSIGNMENT_IDS from config.txt."
        ),
    )
    args = parser.parse_args()

    # Determine assignment IDs: CLI override, else config
    if args.assignments:
        assignment_ids = [
            int(x.strip()) for x in args.assignments.split(",") if x.strip()
        ]
    else:
        assignment_ids = CONFIG_ASSIGNMENT_IDS

    if not assignment_ids:
        print(
            "No assignment IDs provided.\n"
            "Either pass --assignments 12345,23456 or set VERILOG_ASSIGNMENT_IDS in config.txt."
        )
        sys.exit(1)

    print("Using Canvas course:", COURSE_ID)
    print("Assignments to grade (Verilog):", assignment_ids)

    # Load Canvas users (students)
    users = get_canvas_user_dict(BASE_URL, COURSE_ID, CANVAS_API_KEY)
    print(f"Loaded {len(users)} users from Canvas.")

    # Load assignments info
    assignments = get_assignments_by_id(
        BASE_URL, COURSE_ID, CANVAS_API_KEY, assignment_ids
    )
    if not assignments:
        print("No matching assignments found with online_upload type.")
        sys.exit(1)

    for assignment_id in assignment_ids:
        if assignment_id not in assignments:
            print(f"Assignment {assignment_id} not found or not online_upload; skipping.")
            continue

        assignment = assignments[assignment_id]
        points_possible = assignment.get("points_possible", 100)
        print("\n========================================")
        print(f"Grading Assignment {assignment_id}: {assignment['name']}")
        print("Points possible:", points_possible)

        # New testbench convention:
        #   Folder: testbenches/<assignment_id>/
        #   Inside that folder: exactly one .v testbench file (name does not matter).
        #   If multiple .v files exist, we pick the first in sorted order.
        tb_file = get_testbench_for_assignment(assignment_id)
        if tb_file is None:
            # Message already printed by helper; skip this assignment
            continue


        # For each student, get submission and grade if submitted
        for user_id, user_obj in users.items():
            student_id = user_obj["id"]
            student_name = user_obj["name"]

            try:
                submission = get_student_submission(
                    BASE_URL, CANVAS_API_KEY, COURSE_ID, assignment_id, student_id
                )
            except Exception as e:
                print(f"Error retrieving submission for {student_name}: {e}")
                continue

            if not submission:
                print(f"No submission for {student_name}")
                continue

            workflow = submission.get("workflow_state")
            score_already = submission.get("score")

            # Only grade newly submitted or unscored graded submissions
            if workflow not in ("submitted", "graded"):
                continue
            if workflow == "graded" and score_already is not None:
                # Already graded; skip to avoid overwriting unless you want to
                continue

            print(f"  Grading submission for {student_name} (user_id={student_id})")

            score, comment = grade_submission_with_iverilog(
                assignment_id=assignment_id,
                points_possible=points_possible,
                submission_json=submission,
                testbench_path=tb_file,
                # top_module=None  # optional, default is None
            )

            # Post grade + comment back to Canvas
            print(f"    -> Score: {score:.2f} / {points_possible}")
            try:
                post_grade_to_canvas(
                    BASE_URL, COURSE_ID, assignment_id, student_id, score, CANVAS_API_KEY
                )
                #post_submission_comment(
                #    BASE_URL, CANVAS_API_KEY, COURSE_ID, assignment_id, student_id, comment
                #)
            except Exception as e:
                print(f"    Error posting grade/comment for {student_name}: {e}")


CONFIG = load_config("config.txt")
CANVAS_API_KEY = CONFIG.get("CANVAS_API_KEY")
BASE_URL = CONFIG.get("BASE_URL")
COURSE_ID = int(CONFIG.get("COURSE_ID").strip("'"))

# parse assignment IDs from config
# Example in config.txt:
# VERILOG_ASSIGNMENT_IDS = 12345,23456,34567
_assignment_ids_str = CONFIG.get("VERILOG_ASSIGNMENT_IDS", "")
CONFIG_ASSIGNMENT_IDS = [
    int(x.strip()) for x in _assignment_ids_str.split(",") if x.strip()
]

TESTBENCH_DIR = "testbenches"
BUILD_ROOT    = os.path.abspath("verilog_build")

os.makedirs(TESTBENCH_DIR, exist_ok=True)
os.makedirs(BUILD_ROOT, exist_ok=True)

if __name__ == "__main__":
    main()
