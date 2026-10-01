#!/usr/bin/env python3
import socket
import sys
import urllib.error
import urllib.request


def check_endpoint(url, expected_status=200):
    print(f"Checking {url} ... ", end="")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmokeTest"})
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            if status == expected_status:
                print(f"OK ({status})")
                return True
            else:
                print(f"FAIL (Expected {expected_status}, got {status})")
                return False
    except urllib.error.HTTPError as e:
        if e.code == expected_status:
            print(f"OK ({e.code})")
            return True
        print(f"FAIL (HTTP Error {e.code})")
        return False
    except Exception as e:
        print(f"FAIL ({e})")
        return False


def check_socket(host, port):
    print(f"Checking socket {host}:{port} ... ", end="")
    try:
        with socket.create_connection((host, port), timeout=5):
            print("OK")
            return True
    except Exception as e:
        print(f"FAIL ({e})")
        return False


def main():
    print("Starting AURA deployment smoke test...")
    success = True

    # 1. Check frontend
    if not check_endpoint("http://localhost:3000/"):
        success = False

    # 2. Check backend health
    if not check_endpoint("http://localhost:8000/health"):
        success = False

    # 3. Check postgres port
    if not check_socket("localhost", 5432):
        success = False

    # 4. Check redis port
    if not check_socket("localhost", 6379):
        success = False

    if success:
        print("\nAll smoke tests PASSED.")
        sys.exit(0)
    else:
        print("\nSmoke tests FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
