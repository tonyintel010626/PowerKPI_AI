"""
Auto-execute resettarget in PythonSV
This script opens Python and automatically types 'resettarget' command
"""
import subprocess
import time

print("=" * 60)
print("Auto-executing resettarget command in PythonSV")
print("=" * 60)
print("\n[INFO] Launching Python and sending resettarget command...")
print("[INFO] This will reboot the system after ~25-30 seconds initialization\n")

# Create subprocess with stdin pipe
proc = subprocess.Popen(
    ['python'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

# Wait a moment for Python to start
time.sleep(2)

# Send resettarget command
print("[INFO] Sending 'resettarget' command...")
proc.stdin.write("resettarget\n")
proc.stdin.flush()

# Wait a bit then close stdin
time.sleep(3)
proc.stdin.close()

# Read output
print("\n[OUTPUT FROM PYTHONSV]")
print("-" * 60)
stdout, stderr = proc.communicate(timeout=120)
if stdout:
    print(stdout)
if stderr:
    print("Errors:", stderr)

print("-" * 60)
print("\n[INFO] Command executed. System should be resetting...")
