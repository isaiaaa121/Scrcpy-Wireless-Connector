
import subprocess
import secrets
import string
import time
from pathlib import Path
import qrcode

BASE = Path(__file__).resolve().parent
ADB = BASE / "adb.exe"
SCRCPY = BASE / "scrcpy.exe"


def run_adb(args):
    return subprocess.run(
        [str(ADB)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )


def generate_text(length=10):
    characters = string.ascii_letters + string.digits
    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )


def display_qr(data):
    qr = qrcode.QRCode(
        border=4,
        box_size=1
    )
    qr.add_data(data)
    qr.make(fit=True)

    matrix = qr.get_matrix()

    for i in range(0, len(matrix), 2):
        row1 = matrix[i]
        row2 = (
            matrix[i + 1]
            if i + 1 < len(matrix)
            else [False] * len(row1)
        )

        print("".join(
            "▀" if top and not bottom else
            "▄" if bottom and not top else
            "█" if top and bottom else
            " "
            for top, bottom in zip(row1, row2)
        ))


def adb_services():
    result = run_adb(["mdns", "services"])
    services = []

    for line in result.stdout.splitlines():
        parts = line.split()

        if len(parts) >= 3 and "_adb-tls-" in parts[1]:
            services.append({
                "name": parts[0],
                "type": parts[1],
                "address": parts[2]
            })

    return services


def wait_for_service(service_type, name=None, ip=None, seconds=120):
    start_time = time.time()

    while time.time() - start_time < seconds:
        for service in adb_services():

            if service_type not in service["type"]:
                continue

            if name and name not in service["name"]:
                continue

            if ip and not service["address"].startswith(ip + ":"):
                continue

            return service

        time.sleep(1)

    return None


def manual_pairing():
    print("\n=== MANUAL CONNECTION ===")

    address = input("Pairing IP:PORT: ").strip()

    if not address:
        return None

    code = input("Pairing code: ").strip()

    result = run_adb(["pair", address, code])

    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:
        print("[ERROR] Pairing failed.")
        return None

    return input("Connection IP:PORT: ").strip()


def qr_pairing(name, password):
    print("\n[*] Waiting for QR scan (120 seconds)...")

    service = wait_for_service(
        "_adb-tls-pairing._tcp",
        name=name,
        seconds=120
    )

    if not service:
        print("\n[WARNING] Device not detected.")
        return None

    address = service["address"]

    print("\n[OK] Device detected:", address)
    print("[*] Pairing...")

    result = run_adb([
        "pair",
        address,
        password
    ])

    print(result.stdout)
    print(result.stderr)

    if result.returncode != 0:
        print("[ERROR] QR pairing failed.")
        return None

    ip = address.rsplit(":", 1)[0]

    print("\n[*] Searching for ADB connection...")

    service = wait_for_service(
        "_adb-tls-connect._tcp",
        ip=ip,
        seconds=60
    )

    if service:
        return service["address"]

    print("[WARNING] Connection port not found automatically.")

    return input("Connection IP:PORT: ").strip()


def start_scrcpy():
    while True:
        print("\n[*] Starting scrcpy...")

        subprocess.run(
            [str(SCRCPY), "--no-audio"],
            cwd=str(BASE)
        )

        answer = input(
            "\nDo you want to restart scrcpy? (Y/N): "
        ).strip().lower()

        if answer != "y":
            break


def main():
    print("=" * 55)
    print("          SCRCPY WIRELESS CONNECTOR V5.0.1")
    print("=" * 55)

    if not ADB.exists() or not SCRCPY.exists():
        print("\n[ERROR] adb.exe or scrcpy.exe not found.")
        input("Press Enter to exit...")
        return

    name = "studio-" + generate_text()
    password = generate_text()

    data = f"WIFI:T:ADB;S:{name};P:{password};;"

    print("\n=== MANUAL CONNECTION ===")
    print("You can enter the IP address and pairing code manually.")
    print("To use QR pairing, leave the IP address empty.")

    print("\n=== QR CONNECTION ===")
    print("Scan this QR code with your device:\n")

    display_qr(data)

    print("\n---------------------------------------")
    print("Leave the IP address empty to use QR.")
    print("---------------------------------------")

    address = input(
        "\nPairing IP:PORT: "
    ).strip()

    if address:
        code = input("Pairing code: ").strip()

        result = run_adb([
            "pair",
            address,
            code
        ])

        print(result.stdout)
        print(result.stderr)

        if result.returncode != 0:
            print("[ERROR] Manual pairing failed.")
            input("Press Enter to exit...")
            return

        connection = input(
            "Connection IP:PORT: "
        ).strip()

    else:
        connection = qr_pairing(name, password)

        if not connection:
            print("\n=== MANUAL CONNECTION ===")
            connection = manual_pairing()

            if not connection:
                print("[ERROR] Could not establish a connection.")
                input("Press Enter to exit...")
                return

    print("\n[*] Connecting...")

    result = run_adb([
        "connect",
        connection
    ])

    print(result.stdout)
    print(result.stderr)

    devices = run_adb(["devices"])

    if not any(
        line.strip().endswith("\tdevice")
        for line in devices.stdout.splitlines()
    ):
        print("[ERROR] No authorized devices connected.")
        input("Press Enter to exit...")
        return

    print("\n[OK] Connection established!")

    start_scrcpy()

    input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
