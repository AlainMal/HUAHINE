import serial
import threading

def listen_serial(port, baudrate, callback):
    def run():
        ser = serial.Serial(port, baudrate, timeout=1)
        while True:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if line.startswith('$') or line.startswith('!'):
                callback(line)
    threading.Thread(target=run, daemon=True).start()