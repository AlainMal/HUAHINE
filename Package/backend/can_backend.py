import asyncio
from typing import Callable, Optional, Iterable, Set

from Package.CAN_dll import CANDll, CanMsg


class CanBackend:
    """
    Couche Backend simple pour la pile CAN/NMEA2000.

    Responsabilités:
    - gérer l'ouverture/fermeture de la liaison CAN (via CANDll)
    - exposer une API asynchrone pour la lecture en boucle
    - fournir un point d'extension pour la diffusion des trames (callback)
    - déléguer l'envoi des trames à la DLL

    Cette classe encapsule CANDll sans modifier l'existant. Les modules actuels
    peuvent continuer à utiliser CANDll directement. Progressivement, le code UI
    (CANApplication, HUAHINE.py) peut migrer vers CanBackend.
    """

    def __init__(self, dll: Optional[CANDll] = None):
        self._dll = dll
        self._stop_flag: bool = False
        self._on_frame: Optional[Callable[[CanMsg], None]] = None
        self._read_task: Optional[asyncio.Task] = None

    @property
    def dll(self) -> CANDll:
        if self._dll is None:
            # CANDll demande stop_flag et nmea (optionnel). Ici on transmet _stop_flag.
            self._dll = CANDll(self._stop_flag)
        return self._dll

    def set_frame_callback(self, cb: Optional[Callable[[CanMsg], None]]):
        """Enregistre un callback appelé pour chaque trame reçue (thread-safe)."""
        self._on_frame = cb

    # ------------------- Contrôle liaison -------------------
    def open(self, bitrate, acceptance_code, acceptance_mask, flags):
        return self.dll.open(bitrate, acceptance_code, acceptance_mask, flags)

    def close(self):
        if self._read_task:
            # annule la lecture en tâche de fond si active
            self._read_task.cancel()
            self._read_task = None
        self.dll.close()

    def status(self):
        return self.dll.status()

    # ------------------- Lecture -------------------
    async def read_once(self, timeout: float = 2.0) -> Optional[CanMsg]:
        """Lit une seule trame avec un timeout, None si rien."""
        try:
            msg = await asyncio.wait_for(asyncio.to_thread(self.dll.read_dll, self._stop_flag), timeout=timeout)
            return msg
        except asyncio.TimeoutError:
            return None

    async def read_forever(self, timeout: float = 2.0):
        """Boucle de lecture continue jusqu'à stop()."""
        self._stop_flag = False
        while not self._stop_flag:
            msg = await self.read_once(timeout=timeout)
            if msg is None:
                # pas de trame pendant le timeout, on continue
                continue
            if self._on_frame:
                try:
                    self._on_frame(msg)
                except Exception:
                    # on isole les erreurs du callback
                    pass

    def start_reading(self, *, timeout: float = 2.0, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Démarre la lecture en tâche de fond."""
        if self._read_task and not self._read_task.done():
            return self._read_task
        loop = loop or asyncio.get_event_loop()
        self._read_task = loop.create_task(self.read_forever(timeout=timeout))
        return self._read_task

    def stop(self):
        self._stop_flag = True

    # ------------------- Écriture -------------------
    async def send(self, dest: Optional[int | str] = None):
        """Proxy async vers CANDll.send_dll"""
        return await self.dll.send_dll(dest)
