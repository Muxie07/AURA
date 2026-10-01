import subprocess
import time
import sys
import urllib.request
import urllib.error

def check_docker_compose():
    print("Running docker-compose config check...")
    res = subprocess.run(["docker", "compose", "config"], capture_output=True, text=True)
    if res.returncode != 0:
        print("docker-compose config failed!")
        print(res.stderr)
        sys.exit(1)
    print("docker-compose config is valid.")

def ping_health_endpoint(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.urlopen(url)
            if req.getcode() == 200:
                print(f"Healthcheck passed for {url}")
                return True
        except urllib.error.URLError:
            pass
        time.sleep(2)
    print(f"Healthcheck failed for {url} after {timeout} seconds.")
    return False

if __name__ == "__main__":
    check_docker_compose()
    print("Smoke tests are ready to be run by the integration pipeline.")
    sys.exit(0)
