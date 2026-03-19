import ctypes
import asyncio
from Package.Constante import *
from ctypes import Structure, c_ubyte,c_long, c_int, POINTER, Array

class CanData(Array):
    _type_ = c_ubyte
    _length_ = 8

class CanMsg(Structure):
    _fields_ = (
        ("ID", c_long),
        ("TimeStamp", c_long),
        ("flags", c_ubyte),
        ("len", c_ubyte),
        ("data", CanData)
    )

# Erreur sur les fonctions de la dll.
class CanError(Exception):
    pass

# ================================================== Classe Interface dll ==============================================
class CANDll:
    def __init__(self, stop_flag, nmea=None):
        self._etat = None
        self._msg = None
        #self._app = app
        self._stop_flag = stop_flag
        self._handle = None
        self._nmea = nmea
        # Charger la DLL
        try:
            self._dll = ctypes.WinDLL("canusbdrv64.dll")
        except (OSError, FileNotFoundError) as err:
            print("Erreur DLL:", err)
            raise CanError

        # =============== DEFINITION DES FONCTIONS INTERFACE DLL ======================
        #
        # Fonction OPEN
        self._dll.canusb_Open.restype = c_long  # Type de retour : entier long
        # Fonction CLOSE
        self._dll.canusb_Close.argtypes = [c_long]
        # Fonction READ
        self._dll.canusb_Read.argtypes = [c_long, POINTER(CanMsg)]
        self._dll.canusb_Read.restype = c_int
        # Fonction STATUS
        self._dll.canusb_Status.restype = c_int
        # Fonction FLUSH
        self._dll.canusb_Flush.restype = c_int
        self._dll.canusb_Flush.argtypes = [c_long,c_long]
        # Fonction SEND
        self._dll.canusb_Write.restype = c_int
        self._dll.canusb_Write.argtypes = [c_long, POINTER(CanMsg)]
        # Il y en a d'autres, mais pour l'instant ne sont pas utiles

    # Méthode d'ouverture de l'adaptateur. Cette fonction est appelé par le bouton "OPEN".------------------------------
    def open(self, bitrate, acceptance_code, acceptance_mask, flags):
        # Ouvre l'adaptateur et retourne son instance.
        self._handle = self._dll.canusb_Open(None, bitrate, acceptance_code, acceptance_mask, flags)
        if self._handle is None:
            raise CanError("Erreur ouverture canal CAN")
        else:
            return self._handle     # Retourne le handle dont on a besoin pour savoir si c'est ouvert

    # Méthode de lecture des trames du bus CAN en synchrone.-------------------------------------------------------------
    def read_dll(self, stop_flag) -> CanMsg:       # Retourne un pointeur sur le CanMsg
        if self._handle is None:
           raise CanError("Channel not open")

        self._msg = CanMsg()     # Défini le format

        # Boucle pour attendre les trames CAN.
        while not stop_flag:
            if self._handle is None:
                self._handle = 0    # Marquer le handle en entier comme inactif

            if stop_flag:
                return self._msg

            result = self._dll.canusb_Read( self._handle,ctypes.byref(self._msg))

            # Résultat du CAN : on sort si une trame a été reçue : result == CANUSB_OK.
            # Sinon il a des valeurs négatives qui représente différent défaut,
            # dont le ERROR_CANUSB_NO_MESSAGE qui indique qu'il n'a pas reçu de trames.
            if result <= ERROR_CANUSB_OPEN_SUBSYSTEM  and result != ERROR_CANUSB_NO_MESSAGE:
                # On ne traite pas les défauts, mais on le signale.
                print("Défaut CAN : ", str(result))
                # Affiche la fenêtre Status
                # main_window.on_click_status()

            if result == CANUSB_OK: # C'est qu'on a reçu un msg.
                break

        # Une fois une trame reçue, on la retourne
        return self._msg  # Retourne le CanMsg dont on aura besoin pour l'enregistrer

    # Méthode de fermeture de l'adaptateur. ----------------------------------------------------------------------------
    def close(self):
        if self._handle is not None:
            self._dll.canusb_Flush(self._handle, FLUSH_WAIT)
            self._dll.canusb_Close(self._handle)
            self._handle = None

    # Méthode de lecture du status de l'adaptateur. --------------------------------------------------------------------
    def status(self):
        self._etat = self._dll.canusb_Status(self._handle)
        return self._etat

    # Méthode d'écriture des trames du bus CAN en asynchrone. ----------------------------------------------------------
    # On n'envoie que la trame de demande PGN 59904 sur le PGN 126996, pour qu'ils nous répondent
    async def send_dll(self, dest=None):
        print("self._handle HANDLE =", self._handle)
        if self._handle is None or self._handle <= 0:
            print("CAN ERROR Channel not open")
            raise CanError("Channel not open")

        # Si on veut uniquement récupérer leurs adresses détectées
        if dest is None:
            if hasattr(self, "_nmea") and self._nmea is not None and hasattr(self._nmea, "get_participants"):
                participants = self._nmea.get_participants()
                print(f"Participants détectés: {participants}")
                return participants
            else:
                print("Aucune référence NMEA2000 disponible pour récupérer les participants")
                return []

        # Préparer l'envoi d'une requête PGN 126996 à une ou plusieurs destinations
        async def _send_to(one_dest:int) -> bool:
            # Construire correctement le message CAN
            msg = CanMsg()
            # ID étendu: PGN 59904 (0xEA00), priorité 6, source arbitraire, dest = 0x01 -> 0x18EA01EF par exemple
            msg.ID = 0x18EA00EF | (int(one_dest) << 8)
            msg.flags = CAN_EXTENDED
            msg.len = 3
            # Demande de PGN 126996 (Configuration informations)
            msg.data[0] = 0x14
            msg.data[1] = 0xF0
            msg.data[2] = 0x01
            # Remplir le reste à 0 par prudence
            for i in range(3, 8):
                msg.data[i] = 0x00
            # Envoyer
            # Appel C déporté dans un thread
            args = (self._handle, ctypes.byref(msg))
            res_local = await asyncio.to_thread(self._dll.canusb_Write, *args)

            # res_local = self._dll.canusb_Write(self._handle, ctypes.byref(msg))
            print("RÉSULTAT = ", res_local, " pour dest ", one_dest)
            if res_local <= 0:
                print(f"canusb_Write return code: {res_local}")
                raise CanError(f"Erreur écriture CAN: {res_local}")
            return True

        # Si on demande l'envoi à tous les participants détectés
        if dest == 'all' or (isinstance(dest, int) and dest < 0):
            if hasattr(self, "_nmea") and self._nmea is not None and hasattr(self._nmea, "get_participants"):
                participants = await self._nmea.get_participants()
                # participants.add(239)   # On ajoute mon adresse, mais que répondre ?
                if not participants:
                    print("Aucun participant détecté à qui envoyer")
                    return False
                results = []
                for d in participants:
                    try:
                        results.append(await _send_to(d))
                        # Pause pour éviter de saturer le FIFO de transmission
                        await asyncio.sleep(0.2)
                    except Exception as e:
                        print(f"Erreur d'envoi à {d}: {e}")
                        # Même en cas d'erreur, temporiser un peu avant de poursuivre
                        await asyncio.sleep(0.2)
                return all(results) if results else False
            else:
                print("Référence NMEA2000 manquante: envoi à tous impossible")
                return False

        # Sinon, envoi à une destination unique
        return await _send_to(dest)
 # ==================================== FIN DE LA CLASSE CANDll ========================================================