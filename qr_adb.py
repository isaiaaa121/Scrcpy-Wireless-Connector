
import subprocess
import secrets
import string
import time
from pathlib import Path
import qrcode

BASE = Path(__file__).resolve().parent
ADB = BASE / "adb.exe"
SCRCPY = BASE / "scrcpy.exe"


def ejecutar_adb(args):
    return subprocess.run(
        [str(ADB)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )


def generar_texto(longitud=10):
    caracteres = string.ascii_letters + string.digits
    return "".join(
        secrets.choice(caracteres)
        for _ in range(longitud)
    )


def mostrar_qr(datos):
    qr = qrcode.QRCode(
        border=4,
        box_size=1
    )
    qr.add_data(datos)
    qr.make(fit=True)

    matriz = qr.get_matrix()

    for i in range(0, len(matriz), 2):
        fila1 = matriz[i]
        fila2 = (
            matriz[i + 1]
            if i + 1 < len(matriz)
            else [False] * len(fila1)
        )

        print("".join(
            "▀" if arriba and not abajo else
            "▄" if abajo and not arriba else
            "█" if arriba and abajo else
            " "
            for arriba, abajo in zip(fila1, fila2)
        ))


def servicios_adb():
    resultado = ejecutar_adb(["mdns", "services"])
    servicios = []

    for linea in resultado.stdout.splitlines():
        partes = linea.split()

        if len(partes) >= 3 and "_adb-tls-" in partes[1]:
            servicios.append({
                "nombre": partes[0],
                "tipo": partes[1],
                "direccion": partes[2]
            })

    return servicios


def esperar_servicio(tipo, nombre=None, ip=None, segundos=120):
    inicio = time.time()

    while time.time() - inicio < segundos:
        for servicio in servicios_adb():

            if tipo not in servicio["tipo"]:
                continue

            if nombre and nombre not in servicio["nombre"]:
                continue

            if ip and not servicio["direccion"].startswith(ip + ":"):
                continue

            return servicio

        time.sleep(1)

    return None


def emparejar_manual():
    print("\n=== CONEXION MANUAL ===")

    direccion = input("IP:PUERTO de vinculacion: ").strip()

    if not direccion:
        return None

    codigo = input("Codigo de vinculacion: ").strip()

    resultado = ejecutar_adb(["pair", direccion, codigo])

    print(resultado.stdout)
    print(resultado.stderr)

    if resultado.returncode != 0:
        print("[ERROR] No se pudo emparejar.")
        return None

    return input("IP:PUERTO de conexion: ").strip()


def emparejar_qr(nombre, clave):
    print("\n[*] Esperando escaneo QR (120 segundos)...")

    servicio = esperar_servicio(
        "_adb-tls-pairing._tcp",
        nombre=nombre,
        segundos=120
    )

    if not servicio:
        print("\n[AVISO] No se detecto el dispositivo.")
        return None

    direccion = servicio["direccion"]

    print("\n[OK] Dispositivo detectado:", direccion)
    print("[*] Emparejando...")

    resultado = ejecutar_adb([
        "pair",
        direccion,
        clave
    ])

    print(resultado.stdout)
    print(resultado.stderr)

    if resultado.returncode != 0:
        print("[ERROR] Fallo el emparejamiento QR.")
        return None

    ip = direccion.rsplit(":", 1)[0]

    print("\n[*] Buscando conexion ADB...")

    servicio = esperar_servicio(
        "_adb-tls-connect._tcp",
        ip=ip,
        segundos=60
    )

    if servicio:
        return servicio["direccion"]

    print("[AVISO] No se encontro el puerto automaticamente.")

    return input("IP:PUERTO de conexion: ").strip()


def iniciar_scrcpy():
    while True:
        print("\n[*] Iniciando scrcpy...")

        subprocess.run(
            [str(SCRCPY), "--no-audio"],
            cwd=str(BASE)
        )

        respuesta = input(
            "\n¿Quieres volver a abrir scrcpy? (S/N): "
        ).strip().lower()

        if respuesta != "s":
            break


def main():
    print("=" * 55)
    print("          SCRCPY WIRELESS CONNECTOR")
    print("=" * 55)

    if not ADB.exists() or not SCRCPY.exists():
        print("\n[ERROR] No encuentro adb.exe o scrcpy.exe.")
        input("Enter para salir...")
        return

    nombre = "studio-" + generar_texto()
    clave = generar_texto()

    datos = f"WIFI:T:ADB;S:{nombre};P:{clave};;"

    print("\n=== CONEXION MANUAL ===")
    print("Puedes introducir la IP y el codigo manualmente.")
    print("Si quieres usar QR, deja la IP vacia.")

    print("\n=== CONEXION POR QR ===")
    print("Escanea este codigo desde tu dispositivo:\n")

    mostrar_qr(datos)

    print("\n---------------------------------------")
    print("Deja la IP vacia para utilizar el QR.")
    print("---------------------------------------")

    direccion = input(
        "\nIP:PUERTO de vinculacion: "
    ).strip()

    if direccion:
        codigo = input("Codigo de vinculacion: ").strip()

        resultado = ejecutar_adb([
            "pair",
            direccion,
            codigo
        ])

        print(resultado.stdout)
        print(resultado.stderr)

        if resultado.returncode != 0:
            print("[ERROR] Fallo el emparejamiento manual.")
            input("Enter para salir...")
            return

        conexion = input(
            "IP:PUERTO de conexion: "
        ).strip()

    else:
        conexion = emparejar_qr(nombre, clave)

        if not conexion:
            print("\n=== CONEXION MANUAL ===")
            conexion = emparejar_manual()

            if not conexion:
                print("[ERROR] No se pudo establecer la conexion.")
                input("Enter para salir...")
                return

    print("\n[*] Conectando...")

    resultado = ejecutar_adb([
        "connect",
        conexion
    ])

    print(resultado.stdout)
    print(resultado.stderr)

    dispositivos = ejecutar_adb(["devices"])

    if not any(
        linea.strip().endswith("\tdevice")
        for linea in dispositivos.stdout.splitlines()
    ):
        print("[ERROR] No hay dispositivos autorizados conectados.")
        input("Enter para salir...")
        return

    print("\n[OK] Conexion establecida!")

    iniciar_scrcpy()

    input("\nPresiona Enter para cerrar...")


if __name__ == "__main__":
    main()
