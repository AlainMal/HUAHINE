# ========================== Cette application gère la lecture du bus CAN ==============================================
import asyncio
import os
import sys
import platform
import subprocess

from PyQt5.QtCore import QTimer
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QMainWindow, QTreeWidget, QTreeWidgetItem, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QColor, QPixmap

from Package.Constante import *
from Package.CAN_dll import CANDll
from typing import Optional

def resource_path(relative_path):
    """Obtenir le chemin absolu vers les ressources, fonctionne avec PyInstaller"""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# Classe pour éviter que le PC s'arrête pendant l'enregistrement
class SleepPreventer:
    def __init__(self):
        self.os_type = platform.system()
        self.process: Optional[subprocess.Popen] = None

        # Pour Windows
        if self.os_type == 'Windows':
            self.ES_CONTINUOUS = 0x80000000
            self.ES_SYSTEM_REQUIRED = 0x00000001
            self.ES_DISPLAY_REQUIRED = 0x00000002

    def prevent_sleep(self) -> bool:
        """Empêche la mise en veille du système."""
        try:
            if self.os_type == 'Windows':
                import ctypes
                # noinspection PyUnresolvedReferences
                ctypes.windll.kernel32.SetThreadExecutionState(
                    self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED | self.ES_DISPLAY_REQUIRED
                )
                return True

            elif self.os_type == 'Darwin':  # macOS
                self.process = subprocess.Popen(['caffeinate', '-di'])
                return True

            elif self.os_type == 'Linux':
                try:
                    # Utiliser xdg-screensaver directement
                    window_id = subprocess.check_output(
                        ['xdotool', 'getactivewindow']).decode().strip()
                    self.process = subprocess.Popen(
                        ['xdg-screensaver', 'suspend', window_id])
                    return True
                except Exception as e:
                    print(f"Erreur avec xdg-screensaver : {e}")
                    # Alternative avec systemd-inhibit si disponible
                    try:
                        self.process = subprocess.Popen([
                            'systemd-inhibit',
                            '--what=sleep:idle',
                            '--who=MyApp',
                            '--why=Reading CAN bus',
                            'sleep', 'infinity'
                        ])
                        return True
                    except Exception as e2:
                        print(f"Erreur avec systemd-inhibit : {e2}")
                        return False
            return False

        except Exception as e:
            print(f"Erreur lors de l'inhibition de la mise en veille : {e}")
            return False

    def allow_sleep(self) -> bool:
        """Réactive la mise en veille du système."""
        try:
            if self.os_type == 'Windows':
                import ctypes
                # noinspection PyUnresolvedReferences
                ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
                return True

            elif self.os_type == 'Darwin' or self.os_type == 'Linux':
                if self.process:
                    self.process.terminate()
                    self.process = None

                    # Pour Linux, réactiver l'écran de veille si nécessaire
                    if self.os_type == 'Linux':
                        try:
                            window_id = subprocess.check_output(
                                ['xdotool', 'getactivewindow']).decode().strip()
                            subprocess.run(['xdg-screensaver', 'resume', window_id])
                        except (subprocess.SubprocessError, FileNotFoundError) as e:
                            print(f"Erreur lors de la réactivation de l'écran de veille : {e}")
                return True

            return False

        except Exception as e:
            print(f"Erreur lors de la réactivation de la mise en veille : {e}")
            return False

    def __del__(self):
        """Destructeur pour s'assurer que tout est bien nettoyé."""
        self.allow_sleep()

# ****************************************** CLASSE POUR LA LECTURE DU BUS CAN *****************************************
class CANApplication(QMainWindow):
    # Tous les paramètres sont défini dans la classe MainWindow sur HUAHINE.py
    def __init__(self, main_window, temps_reel, file_path, lab_connection, check_file,
                 check_nmea,
                 handle, actions=None):
        super().__init__()

        # Attribuez les actions si elles sont transmises
        self._msg = None
        self._encours = False
        self.actions = actions or {}
        self._main_window = main_window
        # Initialisez les attributs nécessaires ici
        self._fenetre_status = None
        self._status = None
        self._stop_flag = False  # Initialisation du flag stop
        self._can_interface = None
        # Composants CAN et gestion des fichiers
        self._temps_reel = temps_reel
        self._file_path = file_path

        # Construire le chemin relatif vers Alain.ui (qui est dans le répertoire parent)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, "..", "Alain.ui")
        # Charger le fichier .ui
        uic.loadUi(ui_path, self)

        # Passe la référence NMEA2000 depuis la fenêtre principale si disponible
        try:
            nmea_ref = getattr(self._main_window, "_nmea_2000", None)
        except Exception:
            nmea_ref = None

        # Backend évolutif: on conserve CANDll mais on expose aussi un CanBackend optionnel
        try:
            from Package.backend.can_backend import CanBackend
            self._can_backend = CanBackend(CANDll(self._stop_flag, nmea_ref))
            self._can_interface = self._can_backend.dll  # compatibilité existante
        except Exception:
            # Fallback si backend indisponible
            self._can_backend = None
            self._can_interface = CANDll(self._stop_flag, nmea_ref)

        # Gestion des tâches asynchrones et état
        self._handle = handle  # Handle CAN
        self._stop_flag = False  # Drapeau pour arrêter les boucles
        self.loop = None  # Boucle asyncio
        self.task = None  # Gestionnaire de la tâche principale

        # GUI widgets (passés à l'initialisation)
        self.lab_connection = lab_connection
        self.check_file = check_file
        self.check_nmea = check_nmea

        # Connecter les actions aux méthodes locales
        if self.actions.get("actionOpen"):
            self.actions["actionOpen"].triggered.connect(self.on_click_open)
        if self.actions.get("actionClose"):
            self.actions["actionClose"].triggered.connect(self.on_click_close)
        if self.actions.get("actionRead"):
            self.actions["actionRead"].triggered.connect(self.on_click_read)
        if self.actions.get("actionStop"):
            self.actions["actionStop"].triggered.connect(self.on_click_stop)
        if self.actions.get("actionStatus"):
            self.actions["actionStatus"].triggered.connect(self.on_click_status)

        self.sleep_preventer = SleepPreventer()
        self.setWindowIcon(QIcon(resource_path("VoilierImage.ico")))

        # Lance l'open du CANUSB
        self.on_click_open()

    # ====================================== Débuts des méthodes CANApplication ========================================
    # Méthode pour lire le bus CAN -------------------------------------------------------------------------------------
    async def read(self):
        print("On est entré dans la boucle de lecture.")

        self.lab_connection.setText("")  # Initialise le texte
        n = 0
        # Défini les boutons actifs ou désactifs.
        self.update_action_states(open_enabled=False,
                                  read_enabled=False,
                                  close_enabled=True,
                                  stop_enabled=True)

        # Interdit de se mettre en veille
        self.sleep_preventer.prevent_sleep()

        self._stop_flag = False
        self._encours = False

        while not self._stop_flag:
            self._encours = True
            try:
                # Lecture bloquante déplacée dans un thread, avec un timeout
                self._msg = await asyncio.wait_for(
                    asyncio.to_thread(self._can_interface.read_dll, self._stop_flag),
                    timeout=2.0
                )

                if self._msg:  # Si une trame est reçue
                    n += 1

                    # On appelle la fenêtre de la map dès qu'il y a au moins 10 trames reçues
                    if n == 10:
                        self._main_window.on_click_map()

                    self.lab_connection.setText(str(n))  # Mise à jour du nombre de trames reçues.

                    # Appeler la méthode du traitement en TempsReel.
                    self._temps_reel.temps_reel(
                        self._msg,
                        self._file_path,
                        self.check_file.isChecked(),
                        self.check_nmea.isChecked(),
                        self._main_window)  # On lui fait passer le MainWindow().

            except asyncio.TimeoutError:
                print("Aucune trame reçue depuis 2 seconde... Arrêt en cours.")
                self._encours = False
                self._stop_flag = True  # Arrêter la boucle si dépassement de temps
                self.lab_connection.setText("Il n'y a pas de trames arrivées.\nVérifiez que vous êtes bien raccordé. ")
                # Défini les boutons actifs ou dés actifs.
                self.update_action_states(open_enabled=False,
                                          read_enabled=True,
                                          close_enabled=True,
                                          stop_enabled=False)
            except Exception as error:
                self._encours = False
                print(f"Erreur pendant la lecture CAN : {error}")
                print(f"actionOpen attachée à : {self.actionOpen.associatedWidgets()}")

        print("Tâche read() terminée.")
        self._encours = False
        # Ré-autorise la mise en veille du PC.
        self.sleep_preventer.allow_sleep()


    # Méthode pour lancer le Read de manière asynchrone ----------------------------------------------------------------
    async def main(self):
        """Méthode principale pour exécuter read()."""
        try:
            # Lancer la tâche principale et lire les données CAN
            await self.read()
        except asyncio.CancelledError:
            print("Tâche annulée proprement.")
        finally:
            print("Tâches principales terminées.")

    # Méthode pour mettre en Run les taches asynchrones du bus CAN -----------------------------------------------------
    async def run(self):
        """Méthode qui initialise et exécute main."""
        self._stop_flag = False
        try:
            # Vérifie si le handle est valide
            if self._handle == 256:
                await self.main()
        except asyncio.CancelledError:
            print("Tâche annulée dans `run`.")
            raise  # Re-lancer l'exception pour une gestion propre
        except Exception as error:
            print(f"Erreur dans run: {error}")
        finally:
            print("Tâche `run()` terminée.")

    # Méthode du bouton Read, version alternative avec QTimer ----------------------------------------------------------
    def on_click_read(self) -> None:
        print("On est renté dans on_click_read")

        # Arrêter toute tâche existante avant d'en démarrer une nouvelle
        if self.task and not self.task.done():
            self.task.cancel()

        def start_async_task():
            """Fonction interne pour démarrer la tâche asynchrone"""
            try:
                # Obtenir la boucle actuelle
                try:
                    self.loop = asyncio.get_event_loop()
                except RuntimeError:
                    print("Aucune boucle trouvée, création d'une nouvelle")
                    self.loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self.loop)

                if self.loop.is_running():
                    print("Boucle existante détectée")
                    # Créer la tâche dans la boucle existante
                    self.task = self.loop.create_task(self._safe_run(), name="CAN_Read_Task")

                    def task_done_callback(task):
                        try:
                            if task.cancelled():
                                print("Tâche CAN annulée")
                            elif task.exception():
                                print(f"Erreur dans la tâche CAN: {task.exception()}")
                            else:
                                print("Tâche CAN terminée normalement")
                        except Exception as e:
                            print(f"Erreur dans le callback: {e}")

                    self.task.add_done_callback(task_done_callback)
                else:
                    print("Démarrage d'une nouvelle boucle")
                    # Exécuter la coroutine dans une nouvelle boucle
                    self.loop.run_until_complete(self._safe_run())

            except Exception as error:
                print(f"Erreur lors du démarrage de la tâche asynchrone: {error}")

        # Utiliser QTimer pour reporter l'exécution et éviter les conflits de boucle
        QTimer.singleShot(0, start_async_task)

    # Méthode wrapper pour gérer les exceptions de manière asynchrone
    async def _safe_run(self):
        """Wrapper pour exécuter run() avec gestion d'erreur"""
        try:
            await self.run()
        except asyncio.CancelledError:
            print("Tâche CAN annulée proprement")
            raise  # Re-lancer pour une gestion propre
        except Exception as error:
            print(f"Erreur dans _safe_run: {error}")
            # Mettre à jour l'interface en cas d'erreur
            self.update_action_states(open_enabled=False,
                                      read_enabled=True,
                                      close_enabled=True,
                                      stop_enabled=False)
        finally:
            self._encours = False
            print("Tâche CAN terminée")

    # Méthode pour arrêter la lecture ----------------------------------------------------------------------------------
    def on_click_stop(self):
        self.lab_connection.setText("")
        self.update_action_states(open_enabled=False,
                                  read_enabled=True,
                                  close_enabled=True,
                                  stop_enabled=False)

        self._stop_flag = True

        # Annuler la tâche si elle existe avec gestion asynchrone améliorée
        if self.task and not self.task.done():
            print("Annulation de la tâche CAN...")
            self.task.cancel()

            # Programmer une vérification pour s'assurer que la tâche est bien terminée
            if hasattr(self, 'loop') and self.loop and self.loop.is_running():
                # Créer une coroutine de nettoyage avec gestion d'erreur
                async def cleanup_with_error_handling():
                    try:
                        await self._ensure_task_cleanup()
                    except Exception as e:
                        print(f"Erreur lors du nettoyage: {e}")

                # Utiliser create_task au lieu ensure_future (plus moderne)
                self.loop.create_task(cleanup_with_error_handling())

        print("C'est Arrêté ...")

    # Méthode pour s'assurer que la tâche est bien nettoyée
    async def _ensure_task_cleanup(self):
        """S'assure que la tâche est bien terminée"""
        try:
            if self.task and not self.task.done():
                await asyncio.wait_for(self.task, timeout=2.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        except Exception as error:
            print(f"Erreur lors du nettoyage de la tâche: {error}")
        finally:
            self.task = None

    # Méthode pour ouvrir l'adaptateur CANUSB. -------------------------------------------------------------------------
    def on_click_open(self) -> int:
        print("C'est en cours de l'ouverture de l'adaptateur CANUSB.")
        self.setCursor(Qt.CursorShape.WaitCursor)
        # Appelle cette fonction de manière explicite et la fait passer sur "interface".
        self._handle = self._can_interface.open(CAN_BAUD_250K,
                                                CANUSB_ACCEPTANCE_CODE_ALL,
                                                CANUSB_ACCEPTANCE_MASK_ALL,
                                                CANUSB_FLAG_TIMESTAMP)
        print(f"Résultat de l'appel : {self._handle}")
        if self._handle:  # Si l'adaptateur est ouvert.
            self.update_action_states(open_enabled=False,
                                      read_enabled=True,
                                      close_enabled=True,
                                      stop_enabled=False)
            print("C'est ouvert ...........")

            # Lance le serveur Quart, puis on lance la lecture.
            # self._main_window.start_quart_server()
            self.on_click_read()
        else:
            msg = QMessageBox()
            msg.setWindowTitle("OUVERTURE DE L'ADAPTATEUR!")
            msg.setText("Vous n'êtes pas raccordé à l'adaptateur du bus CAN sur l'USB.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setWindowIcon(QIcon("VoilierImage.ico"))

            # Bouton personnalisé
            btnFermer = QPushButton("Quitter")
            msg.addButton(btnFermer, QMessageBox.RejectRole)

            # Icône personnalisée
            pix = QPixmap("VoilierImage.ico")
            msg.setIconPixmap(pix)

            result = msg.exec_()

            if result == QMessageBox.Ok:
                print("OK cliqué → l'application continue")
            elif msg.clickedButton() == btnFermer:
                sys.exit(0)

        self.unsetCursor()
        return self._handle

    # Méthode pour fermer l'adaptateur. --------------------------------------------------------------------------------
    def on_click_close(self) -> None:
        self.setCursor(Qt.CursorShape.WaitCursor)

        self._stop_flag = True

        # Arrêter toutes les tâches asynchrones avec meilleure gestion
        if hasattr(self, 'loop') and self.loop and self.loop.is_running():
            # Créer une tâche pour le nettoyage asynchrone
            cleanup_task = asyncio.create_task(self.cleanup_tasks(), name="CAN_Cleanup")

            # Ajouter un callback pour gérer la fin du nettoyage
            def on_cleanup_done(future):
                try:
                    future.result()  # Récupérer le résultat ou relancer l'exception
                    print("Nettoyage des tâches CAN terminé")
                except Exception as error:
                    print(f"Erreur lors du nettoyage CAN: {error}")

            cleanup_task.add_done_callback(on_cleanup_done)

        # Fermeture de l'adaptateur
        if self._handle == 256:
            self._can_interface.close()  # Ferme l'adaptateur
            print("C'est complètement arrêté, sur le bouton de fermeture")
            # Met les boutons dans l'état voulu
            self.update_action_states(open_enabled=True,
                                      read_enabled=False,
                                      close_enabled=False,
                                      stop_enabled=False)
            self._handle = None

        self.lab_connection.setText("")
        self.unsetCursor()
        return None

    # Méthode pour ouvrir la fenêtre des Status ------------------------------------------------------------------------
    def on_click_status(self):
        try:
            # Si la fenêtre est déjà ouverte, on la ferme
            if self._fenetre_status is not None and self._fenetre_status.isVisible():
                self._fenetre_status.close()
                self._fenetre_status = None
                return None

            if self._handle != 256:
                self._status = 0

            if self._encours: # Si on est en cours de lecture
                self._status = self._can_interface.status()

            print("STATUS = " + str(self._status))

            # Créer la fenêtre `FenetreStatus` avec une référence vers la fenêtre principale (passée dans "self.main_window")
            self._fenetre_status = FenetreStatus(self._status, self._handle, self._main_window)
            # Afficher la fenêtre des Status
            self._fenetre_status.show()
            # On aligne la fenêtre
            self._fenetre_status.align_with_main_window()
            return self._fenetre_status

        except Exception as e:
            print(f"Erreur lors de l'ouverture de la fenêtre Status : {e}")
            return None

    # Méthode qui ferme la fenêtre Status -----------------------------------------------------------------------------
    def fermer_fenetre_status(self):
        """Méthode pour fermer la fenêtre de statut"""
        if self._fenetre_status:  # Vérifiez si la fenêtre existe
            self._fenetre_status.close()  # Fermer la fenêtre
            self._fenetre_status = None  # Réinitialise la référence

    # Méthode pour nettoyer et arrêter toutes les tâches asynchrones
    async def cleanup_tasks(self):
        """Méthode pour nettoyer proprement toutes les tâches"""
        try:
            print("Démarrage du nettoyage des tâches CAN...")
            self._stop_flag = True

            # Annuler la tâche en cours si elle existe
            if self.task and not self.task.done():
                print("Annulation de la tâche CAN en cours...")
                self.task.cancel()
                try:
                    await asyncio.wait_for(self.task, timeout=3.0)
                    print("Tâche CAN annulée avec succès")
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    print("Timeout ou annulation de la tâche CAN")
                except Exception as error:
                    print(f"Erreur lors de l'annulation de la tâche CAN: {error}")

            # Permettre à la boucle de lecture de se terminer
            await asyncio.sleep(0.1)
            print("Nettoyage des tâches CAN terminé")

        except Exception as error:
            print(f"Erreur lors du nettoyage CAN: {error}")
        finally:
            self.task = None
            self._encours = False

    # Méthode qui active ou désactive les boutons ----------------------------------------------------------------------
    def update_action_states(self, open_enabled=False,
                             read_enabled=False,
                             close_enabled=False,
                             stop_enabled=False):
        self.actions["actionRead"].setEnabled(read_enabled)
        self.actions["actionClose"].setEnabled(close_enabled)
        self.actions["actionStop"].setEnabled(stop_enabled)
        self.actions["actionOpen"].setEnabled(open_enabled)
# *************************************** FIN DE LA CLASSE DE LECTURE **************************************************


# ************************************ FENÊTRE DU STATUS ***************************************************************
class FenetreStatus(QMainWindow):
    def __init__(self, status, handle, main_window=None):
        super(FenetreStatus, self).__init__()
        self._main_window = main_window  # Référence à la fenêtre principale pour alignement

        print("Entrer dans la fenêtre Status")
        self._handle = handle
        self._status = status
        self.setFixedSize(290, 252)
        self.setWindowTitle("Statuts")

        self.setWindowIcon(QIcon(resource_path("VoilierImage.ico")))

        # Création du QTreeWidget
        self._treewidget = QTreeWidget(self)
        self._treewidget.setColumnCount(2)
        self._treewidget.setHeaderLabels(["Désignations", "États"])
        self.setCentralWidget(self._treewidget)

        self._treewidget.setColumnWidth(0, 230)  # Définit la largeur de la première colonne à 230 pixels
        self._treewidget.setColumnWidth(1, 1)

        # Remplir le TreeWidget.
        self.remplir_treewidget()

    # ======================================= DEBUT DES MÉTHODES STATUS ================================================
    # Méthode qui aligne la fenêtre status contre la fenêtre principale ------------------------------------------------
    def align_with_main_window(self):
        if self._main_window:
            # Récupérer les coordonnées de frameGeometry de la fenêtre principale
            main_geometry = self._main_window.frameGeometry()

            # Calculer les coordonnées pour FenetreStatus (en haut et à droite)
            new_x = main_geometry.x() + main_geometry.width() + 10
            new_y = main_geometry.y()

            # Déplacer la fenêtre FenetreStatus
            self.move(new_x, new_y)

    # Méthode pour remplir la TreeView ---------------------------------------------------------------------------------
    def remplir_treewidget(self):
        status_data = (
            ("Pas de défaut", CANSTATUS_NO_ERROR),
            ("Adaptateur pas connecté", CANSTATUS_NO_CONNECT),
            ("Buffer de réception plein", CANSTATUS_RECEIVE_FIFO_FULL),
            ("Buffer de transmission plein", CANSTATUS_TRANSMIT_FIFO_FULL),
            ("Avertissement d'erreurs", CANSTATUS_ERROR_WARNING),
            ("Surcharge des Données", CANSTATUS_DATA_OVERRUN),
            ("Erreur passive", CANSTATUS_ERROR_PASSIVE),
            ("Défaut d'arbitrage", CANSTATUS_ARBITRATION_LOST),
            ("Erreur sur le bus", CANSTATUS_BUS_ERROR))

        if self._treewidget:
            for index, (designation, status_value) in enumerate(status_data):
                if index == 0:
                    colonne_2 = "X" if self._status == 0 and self._handle == 256 else ""
                elif index == 1:
                    colonne_2 = "X" if self._handle != 256 else ""
                else:
                    colonne_2 = "X" if self._status == status_value else ""

                item = QTreeWidgetItem([designation, colonne_2])

                # Appliquer une couleur de fond alternée
                if index % 2 == 0:
                    item.setBackground(0, QColor("#f0f0f0"))  # Colonne 0
                    item.setBackground(1, QColor("#f0f0f0"))  # Colonne 1

                self._treewidget.addTopLevelItem(item)
            print("TREEWIDGET REMPLI")
# *************************************** FIN DE LA FENÊTRE STATUS *****************************************************
