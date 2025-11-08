#!/usr/bin/env python3
import os
import time
import shutil
import subprocess
import signal
import re

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

def run(cmd, timeout=300):
    try:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        return 124
    except Exception:
        return 1

def _run_out(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           text=True, timeout=timeout)
        return r.returncode, (r.stdout or "")
    except Exception:
        return 1, ""

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


# Security checkupdates
def security_checkupdate():
    ok = True
    if shutil.which("checkupdates"):
        ok = run(["checkupdates"], timeout=60) in (0, 2)
    if shutil.which("ufw"):
        run(["sudo", "-n", "ufw", "reload"], timeout=5)
    return ok

# VPN connection
def vpn_run():
    run(["protonvpn", "connect"], timeout=60)
    time.sleep(5)

    rc, out = _run_out(["ip", "-o", "addr"], timeout=5)
    if rc == 0:
        for line in out.splitlines():
            if ("proton" in line or "pvpn" in line) and "inet " in line:
                print("[VPN] Tunnel detected after first attempt.")
                return True

    run(["protonvpn", "connect"], timeout=60)
    time.sleep(1)
    rc, out = _run_out(["ip", "-o", "addr"], timeout=5)
    if rc == 0:
        for line in out.splitlines():
            if ("proton" in line or "pvpn" in line) and "inet " in line:
                print("[VPN] Tunnel detected after second attempt.")
                return True

    print("[VPN] Connection failed after two attempts.")
    return False


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
        feed(p, "Updating AUR (paru)...", 30)
        run(["/usr/bin/paru", "-Syu", "--noconfirm"])
    else:
        feed(p, "AUR helper not found. Skipping.", 30)
        time.sleep(3)

    # VPN
    feed(p, "VPN check...", 40)
    time.sleep(0.5)
    if vpn_run():
        feed(p, "VPN is connected.", 50)
    else:
        feed(p, "VPN connection failed.", 50)
    time.sleep(0.5)

    # Start Docker
    feed(p, "Starting Docker...", 60)
    time.sleep(0.5)
    if start_docker():
        feed(p, "Docker is running.", 70)
        time.sleep(0.5)
    else:
        feed(p, "Docker failed to start.", 70)
        time.sleep(3)

    # Security checks
    feed(p, "Security checkupdates...", 80)
    time.sleep(0.5)
    if security_checkupdate():
        feed(p, "Security update...", 90)
        time.sleep(0.5)
    else:
        feed(p, "Security failed to update.", 90)
        time.sleep(3)


    # Finish
    feed(p, "Finishing...", 99)
    time.sleep(0.5)
    feed(p, "✅ All systems are ready.", 100)
    close_window(p, 3)

if __name__ == "__main__":
    main()
