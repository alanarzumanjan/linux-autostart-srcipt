#!/usr/bin/env python3
import os
import time
import shutil
import subprocess
import signal

def start_progress():
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
    env.setdefault("GDK_BACKEND", "x11")
    proc = subprocess.Popen(
        ["zenity", "--progress",
         "--title=System Update",
         "--text=Preparing...",
         "--percentage=0",
         "--no-cancel",
         "--auto-kill"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env
    )
    return proc

def feed(proc, text, percent):
    if proc.poll() is not None:
        return
    proc.stdin.write(f"# {text}\n".encode())
    proc.stdin.write(f"{int(percent)}\n".encode())
    proc.stdin.flush()

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode

def has_internet(host="archlinux.org"):
    return run(["ping", "-c", "1", "-W", "2", host]) == 0

def close_window(proc, delay_seconds):
    time.sleep(delay_seconds)
    try:
        proc.stdin.close()
    except Exception:
        pass
    try:
        proc.wait(timeout=1.0)
        return
    except Exception:
        pass
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=0.7)
        return
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass

# Docker start
def start_docker():
    if run(["systemctl", "--user", "start", "docker"]) == 0:
        return True # try rootless (user service)

    if run(["sudo", "-n", "systemctl", "start", "docker.service"]) == 0:
        return True # try system-wide (requires sudo NOPASSWD or pre-enabled service)
   
    run(["sudo", "-n", "systemctl", "start", "docker.socket"])  # socket activation fallback
    return run(["sudo", "-n", "systemctl", "is-active", "--quiet", "docker.service"]) == 0

def main():
    time.sleep(5)  # let session/network come up

    p = start_progress()
    time.sleep(0.2)

    feed(p, "Checking network...", 10)
    if not has_internet():
        feed(p, "No internet. Skipping updates.", 99)
        time.sleep(3)
        feed(p, "All is updated", 100)
        close_window(p, 3)
        return

    # Update system
    feed(p, "Updating system (pacman)...", 20)
    run(["sudo", "-n", "/usr/bin/pacman", "-Syu", "--noconfirm"])

    if shutil.which("paru"):
        feed(p, "Updating AUR (paru)...", 40)
        run(["sudo", "-n", "/usr/bin/paru", "-Syu", "--noconfirm"])
    else:
        feed(p, "AUR helper not found. Skipping.", 40)
        time.sleep(3)

    # VPN connection
    feed(p, "VPN Connection...", 60)
    time.sleep(1)
    vpn_bin = "/usr/bin/protonvpn" if os.path.exists("/usr/bin/protonvpn") else "protonvpn"

    try:
        rc = subprocess.run([vpn_bin, "connect"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=25).returncode
    except subprocess.TimeoutExpired:
        rc = 1

    if rc == 0:
        feed(p, "VPN is connected.", 70)
        time.sleep(1)
    else:
        feed(p, "VPN connection failed.", 70)
        time.sleep(1)

    # Start Docker
    feed(p, "Starting Docker...", 80)
    time.sleep(1)
    if start_docker():
        feed(p, "Docker is running.", 90)
        time.sleep(1)
    else:
        feed(p, "Docker failed to start.", 90)
        time.sleep(3)

    # Finish
    feed(p, "Finishing...", 99)
    time.sleep(1)
    feed(p, "All Tasks is Done", 100)
    close_window(p, 3)

if __name__ == "__main__":
    main()
