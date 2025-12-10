# Canvas Verilog Autograder

## Overview

This project provides a **fully automated Verilog autograding system integrated with Canvas**, designed for ECE courses where students submit Verilog `.v` files for assignments.  

The tool:

- Retrieves submissions from Canvas using the REST API.
- Downloads and compiles each student's Verilog files using **Icarus Verilog**.
- Locates a testbench inside a **per‑assignment folder**:
  - `testbenches/<assignment_id>/`
  - The folder may contain any number of `.v` files.
  - The autograder picks the first `.v` file alphabetically.
  - If the folder does not exist → it is **created automatically**.
  - If the folder exists but contains **no `.v` files** → the assignment is skipped.
- Runs simulation in a sandboxed per-student folder.
- Parses structured output lines from the testbench (`RESULT:` lines).
- Computes a score and POSTS it directly back to Canvas.
- Posts the detailed grading comment to SpeedGrader.
- Supports:
  - Assignment selection via **config.txt**
  - Optional command-line overrides  
  - Automatic inclusion of Canvas **Test Student**  

---

# Folder Structure

```
project_root/
│
├── canvas_api.py               # Canvas API helper functions
├── grade_verilog_canvas.py     # Main autograder script
├── main.py                     # GPT-based autograder (optional)
├── config.txt                  # Canvas config + assignment IDs
│
├── testbenches/                
│     ├── 12345/                # One folder per assignment ID
│     │     └── my_tb.v         # Chosen automatically
│     ├── 23456/
│     │     └── tb.v
│     └── ...
│
└── verilog_build/              # Auto-generated student-by-student build folders
```

---

# Installation Guide

## 1. Install Python

Requires **Python 3.9+**  
https://www.python.org/downloads/

Verify:

```
python --version
```

---

## 2. Install Required Python Packages

```
pip install requests
```

---

## 3. Install Icarus Verilog

### Windows
1. Download from: https://bleaklow.com/icarus_verilog/
2. Install normally  
3. Verify PATH setup:
   ```
   iverilog -v
   vvp -v
   ```

### macOS (Homebrew)

```
brew install icarus-verilog
```

### Linux (APT example)

```
sudo apt-get install iverilog
```

---

# Canvas Configuration

Inside `config.txt`:

```
CANVAS_API_KEY = your_canvas_token
BASE_URL = https://uncc.instructure.com/api/v1
COURSE_ID = '12345'

# UPDATED: list of assignments to autograde (comma-separated)
VERILOG_ASSIGNMENT_IDS = 12345,23456,34567
```

Notes:

- The script automatically retrieves students **including the Canvas Test Student**.
- The assignment list **now lives in config.txt**.
- You may still override the assignment list at runtime using `--assignments`.

---

# Testbench Folder Structure

The autograder now uses **one folder per assignment**, not a single tb file.

For assignment **12345**:

```
testbenches/12345/
```

Place **at least one** testbench `.v` file in this folder.

- If the folder **doesn't exist**:
  - The tool creates it automatically  
  - Prints a message  
  - Skips the assignment until you add a `.v` file
- If the folder contains **multiple** `.v` files:
  - The tool picks the **alphabetically first** file
- If the folder contains **zero** `.v` files:
  - Prints an error  
  - Skips the assignment

### Testbench Requirements

Your testbench must print structured grading lines:

```verilog
$display("RESULT: test1 PASS");
$display("RESULT: test2 FAIL expected=%0d got=%0d", exp, got);
```

---

# How to Run the Autograder

## Default mode — use assignment IDs from config.txt

```
python grade_verilog_canvas.py
```

## Override mode — provide assignment list manually

```
python grade_verilog_canvas.py --assignments 23456
```

or:

```
python grade_verilog_canvas.py --assignments 23456,34567
```

---

# Autograding Flow

For each assignment:

1. The tool selects a testbench from:
   ```
   testbenches/<assignment_id>/
   ```
2. Retrieves student submissions.
3. Creates a per-student build folder:
   ```
   verilog_build/a<assignment_id>_u<student_id>/
   ```
4. Downloads attached `.v` files (names do **not** matter).
5. Compiles the DUT + testbench using Icarus Verilog.
6. Simulates using `vvp`.
7. Parses `RESULT:` lines to compute the score.
8. Posts the grade and feedback comment to Canvas.

---

# Troubleshooting

### Testbench directory created but empty
Add at least one `.v` file to:
```
testbenches/<assignment_id>/
```

### "No such file or directory" from iverilog
The build system now uses:
- Absolute paths for build directories  
- Relative filenames inside the build directory  

This eliminates most path issues.

### Simulation produces no RESULT lines
Your testbench must contain:

```verilog
$display("RESULT: ...");
```

### Student code fails to compile
Canvas comment will include the compiler error output.