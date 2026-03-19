import socket
import threading


def listen_udp(port: int, callback):
    """
    Écoute les trames NMEA0183 sur un port UDP donné et les transmet à une fonction de traitement.

    Args:
        port (int): Le port UDP à écouter (ex: 10183).
        callback (function): Fonction à appeler avec chaque trame NMEA reçue.
    """
    def run():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', port))
        print(f"[UDP] Écoute sur le port {port}...")
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                line = data.decode('ascii', errors='ignore').strip()
                if line.startswith('$') or line.startswith('!'):
                    callback(line)
            except Exception as e:
                print(f"[UDP] Erreur: {e}")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()