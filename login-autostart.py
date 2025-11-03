import os
import time
import shutil
import subprocess
import signal

def start_progress():
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
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
    # keep window for 'delay_seconds', then close stdin and ensure the process exits
    time.sleep(delay_seconds)
    try:
        proc.stdin.close()
    except Exception:
        pass
    # give zenity a moment to exit gracefully
    try:
        proc.wait(timeout=1.0)
        return
    except Exception:
        pass
    # force close if still alive
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

    feed(p, "Updating system (pacman)...", 40)
    run(["sudo", "-n", "/usr/bin/pacman", "-Syu", "--noconfirm"])

    if shutil.which("paru"):
        feed(p, "Updating AUR (paru)...", 80)
        run(["sudo", "-n", "/usr/bin/paru", "-Syu", "--noconfirm"])
    else:
        feed(p, "AUR helper not found. Skipping.", 80)
        time.sleep(1)

    feed(p, "Finishing...", 99)
    time.sleep(3)
    feed(p, "All is updated", 100)
    close_window(p, 3)

if __name__ == "__main__":
    main()
