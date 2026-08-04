
import paramiko
import os
import time
from datetime import datetime
from scp import SCPClient
# HEPIA AMC 2026 — Script de compilation APK automatique
# ==============================================================================
#
# INSTRUCTIONS: modifiez UNIQUEMENT la section "CONFIGURATION ÉTUDIANT" ci-dessous.
# Ne touchez pas au reste du script.
#
# ==============================================================================
#
#  ╔══════════════════════════════════════════════════════════════════════════╗
#  ║                      CONFIGURATION ÉTUDIANT                              ║
#  ║              Modifiez les valeurs ci-dessous pour votre projet           ║
#  ╚══════════════════════════════════════════════════════════════════════════╝

# ------------------------------------------------------------------------------
# 1) INFORMATIONS DE L'APPLICATION
# ------------------------------------------------------------------------------
APP_TITLE   = "Voice_Recorder"          # Nom de l'application sur le système Android
APP_PACKAGE = "org.hepia.amc" # Identifiant unique (format: com.organisation.nom)
APP_VERSION = "1.0.0"                   # Numéro de version (ex: 1.0.0, 2.3.1)

# ------------------------------------------------------------------------------
# 2) PERMISSIONS ANDROID
#    Décommentez les lignes dont votre application a besoin.
#    Le script détecte aussi automatiquement certaines permissions dans votre code.
# ------------------------------------------------------------------------------
APP_PERMISSIONS = [
    #"CAMERA",                   # ← Caméra (photos/vidéo)
    "INTERNET",                 # ← Connexion réseau/internet
    # "ACCESS_FINE_LOCATION",     # ← GPS précis
    # "ACCESS_COARSE_LOCATION",   # ← Localisation approximative
    # "WRITE_EXTERNAL_STORAGE",   # ← Écriture sur la carte SD
    # "READ_EXTERNAL_STORAGE",    # ← Lecture sur la carte SD
    # "VIBRATE",                  # ← Vibreur
    "RECORD_AUDIO",             # ← Microphone
    # "BLUETOOTH",                # ← Bluetooth
    # "ACCESS_WIFI_STATE",        # ← État du Wi-Fi
]

# Extensions de fichiers transférées sur la VM et embarquées dans l'APK.
# Ne retirez pas '.py', '.kv', '.spec' — ils sont indispensables.
SOURCE_EXTENSIONS = ('.py', '.kv', '.spec')

# Mettre True uniquement pour forcer un rebuild "propre" (supprime le cache buildozer).
RESET_REMOTE_CACHE = False

# ------------------------------------------------------------------------------
# 3) CONNEXION À LA VM  (adresse fournie par l'enseignant)
# ------------------------------------------------------------------------------
VM_HOST     = "10.136.27.137"      # ← Remplacez XXX par l'adresse fournie
VM_PORT     = 22
VM_USERNAME = "student"
VM_PASSWORD = "rUpzi3-zinjac-wihxid" # ← Remplacez par votre mot de passe

# ------------------------------------------------------------------------------
# 4) OPTIONS AVANCÉES  (modifier uniquement si vous savez ce que vous faites)
# ------------------------------------------------------------------------------
# Espace disque minimum requis sur la VM (en GB).
MIN_FREE_SPACE_GB = 3

# Temps estimé de compilation affiché à l'écran (en minutes).
FIRST_COMPILE_TIME  = 10   # Première compilation (SDK/NDK à télécharger)
NORMAL_COMPILE_TIME = 3    # Compilations suivantes (cache réutilisé)

# ==============================================================================
#  ╔══════════════════════════════════════════════════════════════════════════╗
#  ║           🔒  NE PAS MODIFIER EN DESSOUS DE CETTE LIGNE                 ║
#  ╚══════════════════════════════════════════════════════════════════════════╝
# ==============================================================================

# Dossier du projet local et dossier distant (fixe pour conserver le cache buildozer)
LOCAL_PROJECT_DIR   = "."
VM_PROJECT_DIR      = "/home/student/projets"
REMOTE_PROJECT_NAME = f"apk_{APP_PACKAGE.replace('.', '_')}"

# Logs
LOGS_DIR  = os.path.join(LOCAL_PROJECT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE  = os.path.join(LOGS_DIR, f"buildozer_{TIMESTAMP}.log")

START_TIME             = None
compilation_start_time = None


# ==============================================================================
# UTILITAIRES GÉNÉRAUX
# ==============================================================================

def log_message(message, is_error=False):
    """Affiche et sauvegarde un message dans le fichier log."""
    timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix       = "ERROR" if is_error else "INFO"
    full_message = f"[{timestamp}] {prefix}: {message}"
    print(full_message, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")


def format_size(bytes_size):
    """Convertit des octets en format lisible (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


# ==============================================================================
# RECHERCHE AUTOMATIQUE D'ADB SUR WINDOWS
# ==============================================================================

def find_adb_executable():
    """
    Recherche l'exécutable adb sur Windows sans nécessiter de droits admin.

    Ordre de recherche :
      1. 'adb' dans le PATH système (si déjà configuré)
      2. Dossiers Android Studio / SDK courants dans le profil utilisateur
      3. Dossiers Platform-Tools téléchargés à la main dans le profil utilisateur
      4. Dossiers Program Files (lecture seule, pas besoin d'être admin)

    Retourne le chemin complet vers adb.exe, ou None si introuvable.
    """
    import subprocess
    import shutil

    # ── 1. PATH système ──────────────────────────────────────────────────────
    adb_in_path = shutil.which("adb")
    if adb_in_path:
        return adb_in_path

    # ── 2. Dossiers courants dans le profil utilisateur ──────────────────────
    user_profile = os.environ.get("USERPROFILE", "")
    local_app    = os.environ.get("LOCALAPPDATA", "")
    app_data     = os.environ.get("APPDATA", "")

    candidates = []

    # Android Studio (installé sans droits admin via l'installeur utilisateur)
    if local_app:
        candidates += [
            os.path.join(local_app, "Android", "Sdk", "platform-tools", "adb.exe"),
            os.path.join(local_app, "Android", "sdk", "platform-tools", "adb.exe"),
        ]

    # Dossier utilisateur classique
    if user_profile:
        candidates += [
            os.path.join(user_profile, "AppData", "Local", "Android", "Sdk", "platform-tools", "adb.exe"),
            os.path.join(user_profile, "Android", "Sdk", "platform-tools", "adb.exe"),
            os.path.join(user_profile, "platform-tools", "adb.exe"),
            os.path.join(user_profile, "Downloads", "platform-tools", "adb.exe"),
            os.path.join(user_profile, "Desktop",   "platform-tools", "adb.exe"),
            os.path.join(user_profile, "Documents", "platform-tools", "adb.exe"),
        ]

    # ── 3. Program Files (lecture seule – pas besoin d'être admin) ───────────
    for pf_env in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        pf = os.environ.get(pf_env, "")
        if pf:
            candidates += [
                os.path.join(pf, "Android", "android-sdk", "platform-tools", "adb.exe"),
                os.path.join(pf, "Android Studio", "sdk", "platform-tools", "adb.exe"),
            ]

    # ── 4. Vérification ──────────────────────────────────────────────────────
    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


def get_adb_path():
    """
    Retourne le chemin vers adb à utiliser dans les subprocess.
    Affiche un message pédagogique si adb n'est pas trouvé.
    """
    adb = find_adb_executable()
    if adb:
        log_message(f"✅ ADB trouvé: {adb}")
    else:
        print()
        print("⚠️  ADB introuvable sur cet ordinateur.")
        print("   Pour installer Android Platform Tools (sans droits admin) :")
        print("   1. Téléchargez platform-tools depuis:")
        print("      https://developer.android.com/studio/releases/platform-tools")
        print("   2. Décompressez le zip dans votre dossier Documents ou Bureau.")
        print("   3. Relancez ce script.")
        print()
    return adb


# ==============================================================================
# ESPACE DISQUE SUR LA VM
# ==============================================================================

def get_disk_usage(client):
    """Récupère l'utilisation du disque sur la VM."""
    try:
        stdin, stdout, stderr = client.exec_command("df -B1 /home | tail -1")
        output = stdout.read().decode('utf-8').strip()
        if output:
            parts     = output.split()
            total     = int(parts[1])
            used      = int(parts[2])
            available = int(parts[3])
            percent   = parts[4]
            return {
                'total': total, 'used': used, 'available': available, 'percent': percent,
                'total_gb': total / (1024**3), 'used_gb': used / (1024**3),
                'available_gb': available / (1024**3)
            }
    except Exception as e:
        log_message(f"Erreur lors de la vérification de l'espace disque: {e}", is_error=True)
    return None


def get_project_sizes(client):
    """Liste tous les projets avec leur taille."""
    try:
        stdin, stdout, stderr = client.exec_command(
            f"du -sb {VM_PROJECT_DIR}/*/ 2>/dev/null | sort -rn"
        )
        output   = stdout.read().decode('utf-8').strip()
        projects = []
        if output:
            for line in output.split('\n'):
                parts = line.split('\t')
                if len(parts) == 2:
                    size = int(parts[0])
                    path = parts[1]
                    name = os.path.basename(path.rstrip('/'))
                    stdin2, stdout2, stderr2 = client.exec_command(f"stat -c %Y {path}")
                    timestamp = stdout2.read().decode('utf-8').strip()
                    if timestamp:
                        mod_time = datetime.fromtimestamp(int(timestamp))
                        projects.append({
                            'name': name, 'path': path, 'size': size,
                            'size_mb': size / (1024**2), 'modified': mod_time
                        })
        return projects
    except Exception as e:
        log_message(f"Erreur lors de la récupération des projets: {e}", is_error=True)
    return []


def display_disk_info(disk_info):
    """Affiche les informations sur l'espace disque."""
    print("\n" + "="*70)
    print("💾 ESPACE DISQUE SUR LA VM")
    print("="*70)
    print(f"Total:       {format_size(disk_info['total']):>12} ({disk_info['total_gb']:.1f} GB)")
    print(f"Utilisé:     {format_size(disk_info['used']):>12} ({disk_info['used_gb']:.1f} GB) - {disk_info['percent']}")
    print(f"Disponible:  {format_size(disk_info['available']):>12} ({disk_info['available_gb']:.1f} GB)")
    print("="*70)


def check_and_manage_disk_space(client):
    """Vérifie l'espace disque et gère le nettoyage si nécessaire."""
    disk_info = get_disk_usage(client)
    if not disk_info:
        log_message("Impossible de vérifier l'espace disque, continuation...", is_error=False)
        return True

    display_disk_info(disk_info)
    available_gb = disk_info['available_gb']

    if available_gb >= MIN_FREE_SPACE_GB:
        print(f"✅ Espace disponible suffisant ({available_gb:.1f} GB >= {MIN_FREE_SPACE_GB} GB)\n")
        return True

    print(f"\n⚠️  ESPACE DISQUE INSUFFISANT!")
    print(f"   Disponible: {available_gb:.1f} GB")
    print(f"   Requis:     {MIN_FREE_SPACE_GB} GB minimum\n")

    projects = get_project_sizes(client)
    if not projects:
        print("⚠️  Aucun projet trouvé à nettoyer.")
        print("   Contactez votre professeur pour libérer de l'espace.")
        return False

    print("📁 PROJETS EXISTANTS SUR LA VM:")
    print("-"*70)
    print(f"{'#':<4} {'Nom du projet':<30} {'Taille':<12} {'Dernière modif.'}")
    print("-"*70)
    for i, project in enumerate(projects, 1):
        mod_str = project['modified'].strftime("%d/%m/%Y %H:%M")
        print(f"{i:<4} {project['name']:<30} {format_size(project['size']):<12} {mod_str}")
    print("-"*70)
    print(f"Total: {len(projects)} projet(s)\n")

    while True:
        print("OPTIONS:")
        print("  • Entrez le NUMÉRO d'un projet à supprimer")
        print("  • Entrez 'a' pour annuler\n")
        choice = input("Votre choix: ").strip().lower()

        if choice == 'a':
            print("\n❌ Opération annulée. Impossible de continuer sans espace suffisant.")
            return False

        try:
            project_num = int(choice)
            if 1 <= project_num <= len(projects):
                selected_project = projects[project_num - 1]
                print()
                print("⚠️  CONFIRMATION DE SUPPRESSION")
                print(f"   Projet: {selected_project['name']}")
                print(f"   Taille: {format_size(selected_project['size'])} ({selected_project['size_mb']:.1f} MB)")
                print(f"   Dernière modification: {selected_project['modified'].strftime('%d/%m/%Y à %H:%M')}\n")
                confirm = input("Tapez 'OUI' pour confirmer la suppression: ").strip().upper()
                if confirm == 'OUI':
                    log_message(f"Suppression du projet: {selected_project['name']}")
                    stdin, stdout, stderr = client.exec_command(f"rm -rf {selected_project['path']}")
                    stdout.channel.recv_exit_status()
                    print(f"✅ Projet '{selected_project['name']}' supprimé avec succès!\n")
                    return check_and_manage_disk_space(client)
                else:
                    print("❌ Suppression annulée.\n")
            else:
                print(f"❌ Numéro invalide. Choisissez entre 1 et {len(projects)}\n")
        except ValueError:
            print("❌ Entrée invalide. Entrez un numéro ou 'a'\n")


# ==============================================================================
# CONNEXION SSH
# ==============================================================================

def execute_command(client, command, show_output=True):
    """Exécute une commande SSH et retourne la sortie."""
    try:
        stdin, stdout, stderr = client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        output      = stdout.read().decode('utf-8')
        error       = stderr.read().decode('utf-8')
        if show_output and output:
            print(output)
        if error and show_output:
            print(f"Avertissement: {error}")
        return output, error
    except Exception as e:
        log_message(f"Erreur lors de l'exécution de la commande: {e}", is_error=True)
        return None, str(e)


def connect_to_vm():
    """Établit une connexion SSH avec la VM."""
    try:
        log_message(f"Connexion à {VM_USERNAME}@{VM_HOST}:{VM_PORT}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=VM_HOST, port=VM_PORT, username=VM_USERNAME,
                       password=VM_PASSWORD, timeout=10)
        log_message("✅ Connexion établie avec succès!")
        return client
    except paramiko.AuthenticationException:
        log_message("❌ Erreur d'authentification. Vérifiez le nom d'utilisateur et le mot de passe.", is_error=True)
    except paramiko.SSHException as e:
        log_message(f"❌ Erreur SSH: {e}", is_error=True)
    except Exception as e:
        log_message(f"❌ Impossible de se connecter à la VM: {e}", is_error=True)
        log_message("Assurez-vous d'être connecté au VPN de l'école!", is_error=True)
    return None


# ==============================================================================
# ANALYSE DES PERMISSIONS
# ==============================================================================

# Permissions qui nécessitent une demande explicite à l'EXÉCUTION sur Android 6+.
# Pour chacune : patterns de détection + code à insérer dans main.py par l'étudiant.
RUNTIME_PERMISSION_INFO = {
    'CAMERA': {
        'permission_constant': 'Permission.CAMERA',
        'description': 'Caméra (Camera widget Kivy ou plyer)',
        'code': """\
from android.permissions import request_permissions, Permission

class MonApp(App):
    def build(self):
        request_permissions([Permission.CAMERA], self._on_permissions)
        return MonWidget()  # votre widget racine habituel

    def _on_permissions(self, permissions, grants):
        if not all(grants):
            print("⚠️  Permission CAMERA refusée par l'utilisateur!")
""",
    },
    'ACCESS_FINE_LOCATION': {
        'permission_constant': 'Permission.ACCESS_FINE_LOCATION',
        'description': 'GPS / localisation',
        'code': """\
from android.permissions import request_permissions, Permission

class MonApp(App):
    def build(self):
        request_permissions([Permission.ACCESS_FINE_LOCATION], self._on_permissions)
        return MonWidget()

    def _on_permissions(self, permissions, grants):
        if not all(grants):
            print("⚠️  Permission LOCATION refusée par l'utilisateur!")
""",
    },
    'RECORD_AUDIO': {
        'permission_constant': 'Permission.RECORD_AUDIO',
        'description': 'Microphone',
        'code': """\
from android.permissions import request_permissions, Permission

class MonApp(App):
    def build(self):
        request_permissions([Permission.RECORD_AUDIO], self._on_permissions)
        return MonWidget()

    def _on_permissions(self, permissions, grants):
        if not all(grants):
            print("⚠️  Permission RECORD_AUDIO refusée par l'utilisateur!")
""",
    },
}

def analyze_code_permissions(project_dir):
    """
    Analyse les fichiers .py ET .kv pour détecter les permissions Android nécessaires.
    Détecte aussi les permissions "dangereuses" qui nécessitent une demande à l'exécution.
    Retourne (issues, warnings, permissions_set, runtime_permissions_needed).
    """
    issues   = []
    warnings = []
    permissions = set()
    runtime_permissions_needed = set()  # permissions dangereuses détectées

    permission_patterns = {
        'CAMERA': {
            'imports':       ['from plyer import camera', 'import cv2', 'import opencv',
                              'from kivy.uix.camera'],
            'code_patterns': ['camera.take_picture(', 'cv2.VideoCapture(', 'Camera('],
            'kv_patterns':   ['Camera:'],
            'permission':    'CAMERA',
            'runtime':       True,   # ← nécessite request_permissions() à l'exécution
        },
        'INTERNET': {
            'imports':       ['import requests', 'import urllib', 'from urllib'],
            'code_patterns': ['requests.get(', 'requests.post(', 'urllib.request.'],
            'kv_patterns':   [],
            'permission':    'INTERNET',
            'runtime':       False,
        },
        'LOCATION': {
            'imports':       ['from plyer import gps'],
            'code_patterns': ['gps.configure(', 'gps.start('],
            'kv_patterns':   [],
            'permission':    'ACCESS_FINE_LOCATION',
            'runtime':       True,
        },
        'STORAGE': {
            'imports':       ['from plyer import filechooser', 'from android.storage'],
            'code_patterns': ['filechooser.open_file(', 'filechooser.save_file('],
            'kv_patterns':   [],
            'permission':    'WRITE_EXTERNAL_STORAGE',
            'runtime':       False,
        },
        'VIBRATE': {
            'imports':       ['from plyer import vibrator'],
            'code_patterns': ['vibrator.vibrate('],
            'kv_patterns':   [],
            'permission':    'VIBRATE',
            'runtime':       False,
        },
        'AUDIO': {
            'imports':       ['from plyer import tts'],
            'code_patterns': ['AudioCapture(', 'SoundLoader.load('],
            'kv_patterns':   [],
            'permission':    'RECORD_AUDIO',
            'runtime':       True,
        },
    }

    # Chemin absolu de CE script — exclu du scan pour ne pas se détecter soi-même
    this_script = os.path.abspath(__file__)

    try:
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')
                       and d not in ['buildozer', 'bin', 'logs', '__pycache__']]
            for file in files:
                is_py = file.endswith('.py')
                is_kv = file.endswith('.kv')
                if not is_py and not is_kv:
                    continue

                filepath = os.path.join(root, file)

                # Ne jamais scanner le script de compilation lui-même
                if os.path.abspath(filepath) == this_script:
                    continue

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.read().split('\n')

                    for perm_name, perm_data in permission_patterns.items():
                        found = False

                        if is_py:
                            # Vérifier les imports
                            for line in lines:
                                if line.strip().startswith('#'):
                                    continue
                                if any(imp in line for imp in perm_data['imports']):
                                    found = True
                                    break
                            # Vérifier les patterns de code
                            if not found:
                                for line in lines:
                                    if line.strip().startswith('#'):
                                        continue
                                    if any(pat in line for pat in perm_data['code_patterns']):
                                        found = True
                                        break

                        if is_kv and not found:
                            # Vérifier les patterns dans les fichiers .kv
                            for line in lines:
                                stripped = line.strip()
                                if stripped.startswith('#'):
                                    continue
                                if any(pat in stripped for pat in perm_data.get('kv_patterns', [])):
                                    found = True
                                    break

                        if found:
                            permissions.add(perm_data['permission'])
                            if perm_data.get('runtime'):
                                runtime_permissions_needed.add(perm_data['permission'])

                except Exception as e:
                    log_message(f"Erreur lors de la lecture de {filepath}: {e}", is_error=True)
    except Exception as e:
        log_message(f"Erreur lors de l'analyse du code: {e}", is_error=True)

    return issues, warnings, permissions, runtime_permissions_needed


def check_runtime_permissions_in_code(project_dir, runtime_permissions_needed):
    """
    Vérifie si request_permissions() est déjà présent dans le code pour chaque
    permission d'exécution nécessaire.
    Retourne la liste des permissions manquantes dans le code.
    """
    if not runtime_permissions_needed:
        return set()

    # Chercher si request_permissions est déjà appelé dans un .py
    has_request_permissions = False
    perms_already_handled   = set()

    this_script = os.path.abspath(__file__)

    try:
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')
                       and d not in ['buildozer', 'bin', 'logs', '__pycache__']]
            for file in files:
                if not file.endswith('.py'):
                    continue
                filepath = os.path.join(root, file)
                if os.path.abspath(filepath) == this_script:
                    continue
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if 'request_permissions' in content:
                        has_request_permissions = True
                        # Vérifier quelles permissions sont déjà gérées
                        for perm in runtime_permissions_needed:
                            short = perm.replace('ACCESS_', '')  # ACCESS_FINE_LOCATION → FINE_LOCATION
                            if perm in content or short in content:
                                perms_already_handled.add(perm)
                except Exception:
                    pass
    except Exception:
        pass

    return runtime_permissions_needed - perms_already_handled


def display_permission_help(issues, warnings, missing_runtime_perms=None):
    """
    Affiche l'aide pour les problèmes de permissions.
    Pour les permissions d'exécution manquantes, affiche le code exact à ajouter
    et BLOQUE la compilation (ces permissions font planter l'app au démarrage).
    Retourne True pour continuer, False pour annuler.
    """
    has_blocking = bool(missing_runtime_perms)
    has_warnings = bool(issues or warnings)

    if not has_blocking and not has_warnings:
        return True

    print("\n" + "="*70)

    # ── Permissions d'exécution manquantes (bloquant) ─────────────────────────
    if missing_runtime_perms:
        print("🚨 PROBLÈME CRITIQUE — VOTRE APPLICATION VA PLANTER AU DÉMARRAGE")
        print("="*70)
        print()
        print("Sur Android 6+, certaines permissions doivent être demandées")
        print("EXPLICITEMENT dans le code Python au moment de l'exécution.")
        print("Déclarer la permission dans buildozer.spec ne suffit pas.")
        print()

        for perm in sorted(missing_runtime_perms):
            info = RUNTIME_PERMISSION_INFO.get(perm)
            if not info:
                continue
            print(f"❌  Permission manquante : {perm}  ({info['description']})")
            print()
            print("    Ajoutez ce code dans votre main.py :")
            print("    " + "─"*60)
            for line in info['code'].split('\n'):
                print(f"    {line}")
            print("    " + "─"*60)
            print()

        print("⛔  Compilation annulée.")
        print("    Corrigez votre main.py puis relancez le script.")
        print("="*70)
        return False  # ← on bloque

    # ── Avertissements non bloquants ──────────────────────────────────────────
    print("⚠️  AVERTISSEMENTS DÉTECTÉS")
    print("="*70)
    if issues:
        print("\n❌ PROBLÈMES CRITIQUES:")
        for issue in issues:
            print(f"   • {issue}")
    if warnings:
        print("\n⚠️  AVERTISSEMENTS:")
        for warning in warnings:
            print(f"   • {warning}")
    print("\n" + "="*70)
    print("Voulez-vous continuer malgré ces avertissements? (o/n): ", end='', flush=True)
    response = input().strip().lower()
    return response in ['o', 'oui', 'y', 'yes']


# ==============================================================================
# CRÉATION DU BUILDOZER.SPEC
# ==============================================================================

def create_buildozer_spec(auto_permissions=None, sdk_path=None, ndk_path=None):
    """
    Crée buildozer.spec en combinant :
      - APP_PERMISSIONS (déclarées manuellement par l'étudiant en haut du fichier)
      - auto_permissions (détectées automatiquement dans le code)
    Si sdk_path/ndk_path sont fournis, ils sont injectés pour éviter le re-téléchargement.
    """
    if auto_permissions is None:
        auto_permissions = set()

    # Union des permissions manuelles et automatiques
    all_permissions = set(APP_PERMISSIONS) | auto_permissions
    permissions_str = ', '.join(sorted(all_permissions)) if all_permissions else ''

    sdk_line = (f"\n# Chemin vers le SDK Android déjà installé (évite le re-téléchargement)\n"
                f"android.sdk_path = {sdk_path}") if sdk_path else ""
    ndk_line = (f"\n# Chemin vers le NDK Android déjà installé (évite le re-téléchargement)\n"
                f"android.ndk_path = {ndk_path}") if ndk_path else ""

    spec_content = f"""[app]

# (str) Titre de votre application
title = {APP_TITLE}

# (str) Nom du package
package.name = {APP_PACKAGE.split('.')[-1]}

# (str) Domaine du package (unique)
package.domain = {'.'.join(APP_PACKAGE.split('.')[:-1])}

# (str) Répertoire source de l'application
source.dir = .

# (list) Fichiers ou répertoires sources à inclure
source.include_exts = {','.join(ext.lstrip('.') for ext in SOURCE_EXTENSIONS)}

# (str) Version de l'application
version = {APP_VERSION}

# (list) Dépendances de l'application
# plyer toujours inclus — requis pour accéléromètre, GPS, vibration, etc.
requirements = python3,kivy,plyer,kivy_garden.graph

# (str) Permissions Android
android.permissions = {permissions_str}

# (int) Version du SDK Android cible
android.api = 31

# (int) Version minimale du SDK Android
# IMPORTANT: valeur minimale 24 avec NDK r25b — en dessous, grpmodule.c
# échoue à compiler (setgrent/getgrent absents de l'API Android < 24)
android.minapi = 24

# (int) Version du NDK Android
android.ndk = 25b
{sdk_line}{ndk_line}

# Ne pas vérifier les mises à jour des outils Android à chaque build
android.accept_sdk_license = True
android.skip_update = True

# (bool) Autoriser la sauvegarde
android.allow_backup = True

# (str) Orientation de l'écran
orientation = landscape

# (bool) Activer le mode plein écran
fullscreen = 0

# (list) Architectures à compiler
android.archs = arm64-v8a

# Correction: évite l'erreur "Permission denied: .kivy/icon" au démarrage
# Kivy utilise le bon répertoire de données interne à l'application
android.private_storage = True

[buildozer]

# (int) Niveau de log
log_level = 2

# (int) Afficher les avertissements
warn_on_root = 1
"""

    spec_path = os.path.join(LOCAL_PROJECT_DIR, "buildozer.spec")
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)

    log_message(f"✅ Fichier buildozer.spec créé: {spec_path}")
    if all_permissions:
        manual = set(APP_PERMISSIONS)
        auto   = auto_permissions - manual
        if manual:
            log_message(f"   Permissions manuelles : {', '.join(sorted(manual))}")
        if auto:
            log_message(f"   Permissions auto-détectées : {', '.join(sorted(auto))}")
    else:
        log_message("   Aucune permission spéciale nécessaire")

    return spec_path


# ==============================================================================
# TRANSFERT DES FICHIERS
# ==============================================================================

def transfer_files_to_vm(client):
    """
    Transfère les fichiers du projet vers la VM (mode rapide, incrémental).
    Réutilise le même dossier distant pour conserver le cache buildozer.
    """
    try:
        remote_project_dir = f"{VM_PROJECT_DIR}/{REMOTE_PROJECT_NAME}"
        log_message(f"Préparation du dossier distant: {remote_project_dir}")
        execute_command(client, f"mkdir -p {remote_project_dir}", show_output=False)

        if RESET_REMOTE_CACHE:
            log_message("🧹 Nettoyage du cache distant (.buildozer/ et bin/) ...")
            execute_command(client,
                f"rm -rf {remote_project_dir}/.buildozer {remote_project_dir}/bin",
                show_output=False)

        log_message("Transfert des fichiers (incrémental)...")
        sftp = client.open_sftp()

        def remote_same_as_local(local_path: str, remote_path: str) -> bool:
            try:
                rstat = sftp.stat(remote_path)
            except (FileNotFoundError, OSError):
                return False
            try:
                lstat = os.stat(local_path)
            except OSError:
                return False
            if rstat.st_size != lstat.st_size:
                return False
            return abs(int(rstat.st_mtime) - int(lstat.st_mtime)) <= 2

        sent    = 0
        skipped = 0

        with SCPClient(client.get_transport()) as scp:
            for root, dirs, files in os.walk(LOCAL_PROJECT_DIR):
                dirs[:] = [d for d in dirs
                           if d not in ['.buildozer', 'bin', '__pycache__', '.git', 'logs']]
                for file in files:
                    if not file.endswith(SOURCE_EXTENSIONS):
                        continue
                    local_path  = os.path.join(root, file)
                    rel_path    = os.path.relpath(local_path, LOCAL_PROJECT_DIR)
                    remote_path = os.path.join(remote_project_dir, rel_path).replace('\\', '/')
                    remote_dir  = os.path.dirname(remote_path)
                    if remote_dir and remote_dir != remote_project_dir:
                        execute_command(client, f"mkdir -p {remote_dir}", show_output=False)
                    if remote_same_as_local(local_path, remote_path):
                        skipped += 1
                        continue
                    scp.put(local_path, remote_path, preserve_times=True)
                    sent += 1

        try:
            sftp.close()
        except Exception:
            pass

        log_message(f"✅ Transfert terminé: {sent} fichier(s) envoyés, {skipped} inchangé(s)")
        log_message(f"✅ Projet distant: {remote_project_dir}")
        return remote_project_dir

    except Exception as e:
        log_message(f"❌ Erreur lors du transfert: {e}", is_error=True)
        return None


# ==============================================================================
# PACKAGES PYTHON SUR LA VM
# ==============================================================================

def check_and_install_missing_packages(client, remote_dir):
    """Vérifie et installe UNIQUEMENT les packages Python manquants sur la VM."""
    log_message("Vérification des packages Python requis...")
    conda_activate = "source $HOME/anaconda3/bin/activate buildozer_venv"
    spec_path      = f"{remote_dir}/buildozer.spec"
    output, _      = execute_command(client, f"grep '^requirements =' {spec_path}", show_output=False)

    if not output:
        log_message("✅ Aucun package supplémentaire requis")
        return

    requirements_line = output.strip()
    if '=' in requirements_line:
        packages_to_check = [
            pkg.strip() for pkg in requirements_line.split('=', 1)[1].strip().split(',')
            if pkg.strip() not in ['python3', 'kivy']
        ]
    else:
        packages_to_check = []

    if not packages_to_check:
        log_message("✅ Tous les packages de base sont déjà installés")
        return

    log_message(f"Packages à vérifier: {', '.join(packages_to_check)}")
    missing_packages = []
    for package in packages_to_check:
        check_cmd = f"{conda_activate} && python3 -c 'import {package}' 2>/dev/null && echo 'OK' || echo 'MISSING'"
        output, _ = execute_command(client, check_cmd, show_output=False)
        if 'MISSING' in output:
            missing_packages.append(package)
            log_message(f"  ❌ {package}: non installé")
        else:
            log_message(f"  ✅ {package}: déjà installé")

    if missing_packages:
        log_message(f"\nInstallation des packages manquants: {', '.join(missing_packages)}")
        for package in missing_packages:
            log_message(f"  Installation de {package}...")
            output, error = execute_command(client,
                f"{conda_activate} && pip install {package}", show_output=False)
            if error and 'Successfully installed' not in output:
                log_message(f"  ⚠️ Avertissement lors de l'installation de {package}", is_error=False)
            else:
                log_message(f"  ✅ {package} installé avec succès")
    else:
        log_message("✅ Tous les packages requis sont déjà installés")


# ==============================================================================
# DÉTECTION SDK/NDK SUR LA VM
# ==============================================================================

def detect_sdk_ndk_paths(client):
    """
    Détecte les chemins du SDK et NDK Android déjà installés sur la VM.
    Retourne (sdk_path, ndk_path) ou (None, None) si non trouvés.
    """
    sdk_candidates = [
        "/home/student/.buildozer/android/platform/android-sdk",
        "/opt/android-sdk",
        "/home/student/Android/Sdk",
        "/home/student/.android/sdk",
    ]
    ndk_candidates = [
        "/home/student/.buildozer/android/platform/android-ndk-r25b",
        "/home/student/.buildozer/android/platform/android-ndk-r25",
        "/opt/android-ndk",
        "/home/student/Android/Ndk",
    ]

    sdk_path = None
    for path in sdk_candidates:
        out, _ = execute_command(client, f"test -d {path} && echo OK", show_output=False)
        if "OK" in (out or ""):
            sdk_path = path
            log_message(f"✅ SDK Android trouvé: {sdk_path}")
            break

    ndk_path = None
    for path in ndk_candidates:
        out, _ = execute_command(client, f"test -d {path} && echo OK", show_output=False)
        if "OK" in (out or ""):
            ndk_path = path
            log_message(f"✅ NDK Android trouvé: {ndk_path}")
            break

    if not sdk_path:
        log_message("ℹ️  SDK Android non trouvé localement - buildozer le téléchargera")
    if not ndk_path:
        log_message("ℹ️  NDK Android non trouvé localement - buildozer le téléchargera")

    return sdk_path, ndk_path


# ==============================================================================
# COMPILATION APK
# ==============================================================================

def build_apk(client, remote_dir):
    """
    Compile l'APK avec buildozer de manière optimisée.
    Lecture de la sortie via un thread dédié pour éviter toute boucle infinie.
    """
    import threading
    import queue

    global compilation_start_time
    compilation_start_time = time.time()

    log_message("Lancement de la compilation...")
    log_message("⏱️  Cela peut prendre quelques minutes...")

    conda_activate      = "source $HOME/anaconda3/bin/activate buildozer_venv"
    check_buildozer_cmd = f"{conda_activate} && which buildozer"
    output, _           = execute_command(client, check_buildozer_cmd, show_output=False)

    if not output or 'buildozer' not in output:
        log_message("❌ Buildozer n'est pas installé sur la VM!", is_error=True)
        log_message("Veuillez exécuter le script d'installation de la VM d'abord.", is_error=True)
        return None, 0

    log_message(f"✓ Buildozer trouvé: {output.strip()}")

    check_cache_cmd = f"test -d {remote_dir}/.buildozer && echo 'EXISTS' || echo 'NEW'"
    output, _       = execute_command(client, check_cache_cmd, show_output=False)
    is_first_build  = 'NEW' in (output or '')

    if is_first_build:
        log_message("ℹ️  Première compilation - le SDK/NDK sera réutilisé si détecté")
        estimated_time = FIRST_COMPILE_TIME
    else:
        log_message("ℹ️  Compilation incrémentale - utilisation du cache existant")
        estimated_time = NORMAL_COMPILE_TIME

    log_message(f"⏱️  Temps estimé: ~{estimated_time} minute(s)")

    build_command = f"{conda_activate} && cd {remote_dir} && buildozer -v android debug 2>&1"

    BUILDOZER_PREFIXES = (
        '# Downloading', '# Installing', '# Compiling',
        '# Building',    '# Unpacking',  '# Copy ',
    )
    EXACT_KEYWORDS = (
        'BUILD SUCCESSFUL', 'BUILD FAILED', 'Package created',
        'error:', 'Error:', 'FAILED', 'Exception',
        'Gradle', 'Collecting ', '[INFO]', '[WARNING]', '[ERROR]',
    )

    def should_log_line(line: str) -> bool:
        if line.startswith(BUILDOZER_PREFIXES):
            return True
        if any(kw in line for kw in EXACT_KEYWORDS):
            return True
        return False

    try:
        stdin, stdout, stderr = client.exec_command(build_command, get_pty=True)
        line_queue = queue.Queue()
        read_done  = threading.Event()

        def reader_thread():
            buffer = b""
            while True:
                try:
                    chunk = stdout.read(1)
                    if not chunk:
                        break
                    buffer += chunk
                    if chunk in (b'\n', b'\r'):
                        line = buffer.decode('utf-8', errors='replace').strip()
                        if line:
                            line_queue.put(line)
                        buffer = b""
                except Exception:
                    break
            if buffer:
                line = buffer.decode('utf-8', errors='replace').strip()
                if line:
                    line_queue.put(line)
            read_done.set()

        t = threading.Thread(target=reader_thread, daemon=True)
        t.start()

        last_progress_time = time.time()
        progress_interval  = 15  # secondes

        while not read_done.is_set() or not line_queue.empty():
            current_time = time.time()
            while not line_queue.empty():
                try:
                    line = line_queue.get_nowait()
                    if should_log_line(line):
                        log_message(line)
                except queue.Empty:
                    break
            if current_time - last_progress_time >= progress_interval:
                elapsed = (current_time - compilation_start_time) / 60
                log_message(f"⏱️  Compilation en cours... ({elapsed:.1f} min écoulées)")
                last_progress_time = current_time
            time.sleep(0.3)

        t.join(timeout=10)
        exit_status = stdout.channel.recv_exit_status()
        build_time  = time.time() - compilation_start_time

        if exit_status == 0:
            log_message(f"✅ Compilation réussie en {build_time/60:.1f} minutes")
            find_apk_cmd = f"find {remote_dir}/bin -name '*.apk' | head -1"
            apk_path, _  = execute_command(client, find_apk_cmd, show_output=False)
            if apk_path:
                apk_path = apk_path.strip()
                log_message(f"APK généré: {apk_path}")
                return apk_path, build_time
            else:
                log_message("❌ Fichier APK introuvable après compilation", is_error=True)
                return None, build_time
        else:
            log_message(f"❌ Échec de la compilation (code de retour: {exit_status})", is_error=True)
            log_message("Consultez le fichier log pour plus de détails.", is_error=False)
            return None, build_time

    except Exception as e:
        build_time = time.time() - compilation_start_time
        log_message(f"❌ Erreur lors de la compilation: {e}", is_error=True)
        return None, build_time


# ==============================================================================
# INSTALLATION SUR TABLETTE ANDROID
# ==============================================================================

def _disable_play_protect(adb):
    """
    Désactive temporairement Google Play Protect via ADB.
    Retourne True si la commande a été envoyée (sans garantie de succès —
    certaines tablettes nécessitent une confirmation manuelle sur l'écran).
    """
    import subprocess
    log_message("Désactivation de Google Play Protect...")
    try:
        # Méthode 1 : settings put global (Android 8+)
        r = subprocess.run(
            [adb, 'shell', 'settings', 'put', 'global',
             'package_verifier_enable', '0'],
            capture_output=True, text=True, timeout=10)
        # Méthode 2 : désactiver la vérification des APKs inconnus
        subprocess.run(
            [adb, 'shell', 'settings', 'put', 'global',
             'verifier_verify_adb_installs', '0'],
            capture_output=True, text=True, timeout=10)
        log_message("✅ Play Protect désactivé via ADB")
        return True
    except Exception as e:
        log_message(f"⚠️ Impossible de désactiver Play Protect automatiquement: {e}",
                    is_error=False)
        return False


def _reenable_play_protect(adb):
    """Réactive Google Play Protect après l'installation."""
    import subprocess
    try:
        subprocess.run(
            [adb, 'shell', 'settings', 'put', 'global',
             'package_verifier_enable', '1'],
            capture_output=True, text=True, timeout=10)
        subprocess.run(
            [adb, 'shell', 'settings', 'put', 'global',
             'verifier_verify_adb_installs', '1'],
            capture_output=True, text=True, timeout=10)
        log_message("✅ Play Protect réactivé")
    except Exception:
        pass


def _do_install(adb, apk_path, timeout=90):
    """
    Tente d'installer l'APK et retourne (success, error_output).
    Utilise -r (replace) et -t (autoriser les APKs de test/debug).
    """
    import subprocess
    result = subprocess.run(
        [adb, 'install', '-r', '-t', apk_path],
        capture_output=True, text=True, timeout=timeout)
    error_output = (result.stdout + result.stderr).strip()
    success = (result.returncode == 0 and 'Success' in result.stdout)
    return success, error_output


def _launch_app(adb, package_name):
    """Lance l'application sur la tablette."""
    import subprocess
    launch_cmd = [adb, 'shell', 'monkey', '-p', package_name,
                  '-c', 'android.intent.category.LAUNCHER', '1']
    result = subprocess.run(launch_cmd, capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        log_message("✅ Application lancée!")
        print("✅ Application lancée sur la tablette!")
    else:
        log_message("⚠️ Échec du lancement automatique", is_error=False)
        print("⚠️ Impossible de lancer automatiquement — lancez l'application manuellement.")


def _ask_launch(adb, package_name):
    """Propose à l'utilisateur de lancer l'application."""
    resp = input("Voulez-vous lancer l'application maintenant? (o/n): ").strip().lower()
    if resp in ['o', 'oui', 'y', 'yes']:
        _launch_app(adb, package_name)


def install_and_launch_on_device(apk_path, package_name):
    """
    Installe et lance l'APK sur un appareil Android connecté en USB.
    Gère automatiquement les cas d'erreur courants :
      • INSTALL_FAILED_VERIFICATION_FAILURE  → Play Protect bloque l'APK debug
      • INSTALL_FAILED_UPDATE_INCOMPATIBLE   → ancienne version avec signature différente
    Recherche adb automatiquement (sans droits admin sur Windows).
    """
    import subprocess

    print("\n" + "="*70)
    print("📱 INSTALLATION SUR TABLETTE ANDROID")
    print("="*70)
    print()
    print("Voulez-vous installer l'APK sur une tablette Android connectée?")
    print("  • Connectez votre tablette en USB")
    print("  • Activez le mode développeur et le débogage USB")
    print()
    response = input("Installer maintenant? (o/n): ").strip().lower()

    if response not in ['o', 'oui', 'y', 'yes']:
        print("\n⏭️  Installation sur tablette ignorée")
        print("="*70)
        return

    # ── Recherche automatique d'adb ──────────────────────────────────────────
    adb = get_adb_path()
    if not adb:
        print("\n❌ ADB non trouvé — installation sur tablette impossible.")
        print("   Voir les instructions ci-dessus pour installer Platform Tools.")
        print("="*70)
        return

    try:
        # Vérifier la version d'adb
        log_message("Vérification de la présence d'adb...")
        result = subprocess.run([adb, 'version'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("\n❌ ADB trouvé mais ne répond pas correctement.")
            print("="*70)
            return

        # Vérifier qu'un appareil est connecté
        log_message("Recherche d'appareils Android connectés...")
        result  = subprocess.run([adb, 'devices'],
                                 capture_output=True, text=True, timeout=10)
        devices = [line for line in result.stdout.split('\n')
                   if line.strip() and not line.startswith('List') and '\tdevice' in line]

        if not devices:
            print("\n❌ Aucun appareil Android détecté!")
            print("   Assurez-vous que:")
            print("   • La tablette est connectée en USB")
            print("   • Le débogage USB est activé")
            print("   • Vous avez autorisé le débogage sur la tablette")
            print()
            print("="*70)
            return

        log_message(f"✅ Appareil détecté: {devices[0].split()[0]}")

        # ── Première tentative d'installation ────────────────────────────────
        log_message("Installation de l'APK sur l'appareil...")
        print("\n⏳ Installation en cours...")
        success, error_output = _do_install(adb, apk_path)

        if success:
            log_message("✅ APK installé avec succès!")
            print("✅ APK installé avec succès!")
            print()
            _ask_launch(adb, package_name)
            return

        # ── Échec — analyse de l'erreur ──────────────────────────────────────
        log_message("❌ Échec de l'installation", is_error=True)
        log_message(f"   Détails adb: {error_output}", is_error=True)
        print(f"❌ Échec de l'installation")
        print(f"   Détails: {error_output}")

        # ────────────────────────────────────────────────────────────────────
        # CAS 1 : INSTALL_FAILED_VERIFICATION_FAILURE
        #   → Google Play Protect bloque les APKs de développement (debug).
        #   → Solution : désactiver Play Protect via ADB, réinstaller,
        #     puis réactiver Play Protect.
        # ────────────────────────────────────────────────────────────────────
        if 'INSTALL_FAILED_VERIFICATION_FAILURE' in error_output:
            print()
            print("⚠️  Google Play Protect a bloqué l'installation.")
            print("   Les APKs de développement (debug) ne sont pas signés par le Play Store.")
            print("   Play Protect doit être désactivé temporairement pour permettre")
            print("   l'installation, puis sera réactivé automatiquement.")
            print()

            # Tentative de désactivation automatique via ADB
            disabled = _disable_play_protect(adb)

            if not disabled:
                # La désactivation automatique a échoué → instructions manuelles
                print("⚠️  La désactivation automatique a échoué.")
                print("   Désactivez Play Protect manuellement sur la tablette :")
                print("   1. Ouvrez le Play Store")
                print("   2. Menu ☰ → Play Protect → Paramètres (roue ⚙️)")
                print("   3. Désactivez « Rechercher des applications nuisibles »")
                print("   4. Appuyez Entrée ici pour réessayer l'installation")
                input("   Appuyez sur Entrée quand c'est fait...")
            else:
                # Laisser le temps à Android d'appliquer le paramètre
                print("   Patientez 3 secondes...")
                time.sleep(3)

            print("⏳ Nouvelle tentative d'installation...")
            success2, error2 = _do_install(adb, apk_path)
            _reenable_play_protect(adb)  # toujours réactiver, succès ou non

            if success2:
                log_message("✅ APK installé avec succès (après désactivation de Play Protect)!")
                print("✅ APK installé avec succès!")
                print()
                _ask_launch(adb, package_name)
            else:
                log_message(f"❌ Échec persistant après désactivation de Play Protect: {error2}",
                            is_error=True)
                print(f"❌ L'installation a encore échoué: {error2}")
                print()
                print("   Solutions alternatives :")
                print("   1. Désactivez Play Protect manuellement (Play Store → Play Protect)")
                print("      puis relancez ce script.")
                print("   2. Transférez l'APK sur la tablette et installez-le")
                print("      manuellement depuis le Gestionnaire de fichiers.")
                print(f"      Fichier APK : {apk_path}")

        # ────────────────────────────────────────────────────────────────────
        # CAS 2 : INSTALL_FAILED_UPDATE_INCOMPATIBLE
        #   → Une version précédente est installée avec une signature différente.
        #   → Solution : désinstaller l'ancienne version, puis réinstaller.
        # ────────────────────────────────────────────────────────────────────
        elif 'INSTALL_FAILED_UPDATE_INCOMPATIBLE' in error_output:
            print()
            print("⚠️  Une ancienne version de l'application est déjà installée sur la tablette.")
            print("   Elle doit être désinstallée avant d'installer la nouvelle version.")
            print()
            resp = input("Désinstaller l'ancienne version et réinstaller? (o/n): ").strip().lower()
            if resp in ['o', 'oui', 'y', 'yes']:
                log_message(f"Désinstallation de {package_name}...")
                uninstall = subprocess.run([adb, 'uninstall', package_name],
                                           capture_output=True, text=True, timeout=30)
                if uninstall.returncode == 0:
                    log_message("✅ Ancienne version désinstallée")
                    print("✅ Ancienne version désinstallée. Réinstallation en cours...")
                    success2, error2 = _do_install(adb, apk_path)
                    if success2:
                        log_message("✅ APK installé avec succès (après désinstallation)!")
                        print("✅ APK installé avec succès!")
                        print()
                        _ask_launch(adb, package_name)
                    else:
                        log_message(f"❌ Échec de la réinstallation: {error2}", is_error=True)
                        print(f"❌ Échec de la réinstallation: {error2}")
                else:
                    log_message("❌ Échec de la désinstallation", is_error=True)
                    print("❌ Impossible de désinstaller l'ancienne version.")
                    print("   Désinstallez-la manuellement depuis la tablette et relancez le script.")
            else:
                print("⏭️  Désinstallation annulée.")

        # ────────────────────────────────────────────────────────────────────
        # CAS 3 : Autre erreur non reconnue
        # ────────────────────────────────────────────────────────────────────
        else:
            print()
            print("   Cause inconnue — essayez les solutions suivantes :")
            print("   • Vérifiez que la tablette a suffisamment d'espace libre.")
            print("   • Débranchez et rebranchez le câble USB, puis relancez.")
            print("   • Installez l'APK manuellement depuis la tablette :")
            print(f"     Fichier APK : {apk_path}")

    except subprocess.TimeoutExpired:
        log_message("❌ Timeout lors de l'installation (>90s)", is_error=True)
        print("❌ Timeout lors de l'installation")
        print("Vérifiez que la tablette est bien connectée et réessayez.")
    except Exception as e:
        log_message(f"❌ Erreur lors de l'installation: {e}", is_error=True)
        print(f"❌ Erreur lors de l'installation: {e}")
    finally:
        print()
        print("="*70)


# ==============================================================================
# TÉLÉCHARGEMENT DE L'APK
# ==============================================================================

def download_apk(client, remote_apk_path):
    """Télécharge l'APK depuis la VM vers le dossier bin/ local."""
    try:
        log_message("Téléchargement de l'APK...")
        output, _ = execute_command(client, f"ls {remote_apk_path}", show_output=False)
        if not output:
            log_message("Aucun fichier APK trouvé", is_error=True)
            return None

        apk_filename  = output.strip().split('\n')[0]
        local_apk_dir = os.path.join(LOCAL_PROJECT_DIR, "bin")
        os.makedirs(local_apk_dir, exist_ok=True)
        local_apk_path = os.path.join(local_apk_dir, os.path.basename(apk_filename))

        with SCPClient(client.get_transport()) as scp:
            scp.get(apk_filename, local_path=local_apk_path)

        apk_size = os.path.getsize(local_apk_path)
        log_message(f"APK téléchargé: {local_apk_path} ({format_size(apk_size)})")
        return local_apk_path

    except Exception as e:
        log_message(f"Erreur lors du téléchargement: {e}", is_error=True)
        return None


# ==============================================================================
# RÉSUMÉ DU BUILD
# ==============================================================================

def save_build_summary(total_time, success=True, apk_path=None):
    """Sauvegarde un résumé du build dans le log."""
    log_message("=" * 70)
    log_message("RÉSUMÉ DU BUILD")
    log_message(f"Application: {APP_TITLE}")
    log_message(f"Package: {APP_PACKAGE}")
    log_message(f"Version: {APP_VERSION}")
    log_message(f"Temps total: {total_time:.1f} secondes ({total_time/60:.1f} minutes)")
    log_message(f"Statut: {'SUCCÈS' if success else 'ÉCHEC'}")
    if success and apk_path:
        log_message(f"Fichier APK: {apk_path}")
    log_message("=" * 70)


# ==============================================================================
# FONCTION PRINCIPALE
# ==============================================================================

def main():
    global START_TIME
    START_TIME = time.time()

    print("\n" + "=" * 70)
    print("    GÉNÉRATION APK AUTOMATIQUE - HEPIA AMC 2026")
    print("=" * 70 + "\n", flush=True)
    print(f"📄 Fichier log: {LOG_FILE}\n")

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 70 + "\n")
        f.write(f"NOUVEAU BUILD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n")

    log_message(f"Application: {APP_TITLE} v{APP_VERSION}")
    log_message(f"Package: {APP_PACKAGE}")
    log_message(f"VM: {VM_USERNAME}@{VM_HOST}")
    log_message("")

    try:
        # Étape 1: Analyser le code pour détecter les permissions
        log_message("ÉTAPE 1: Analyse du code pour détecter les permissions")
        issues, warnings, auto_permissions, runtime_perms = analyze_code_permissions(LOCAL_PROJECT_DIR)

        all_permissions = set(APP_PERMISSIONS) | auto_permissions
        if all_permissions:
            log_message(f"✅ Permissions à intégrer: {', '.join(sorted(all_permissions))}")
        else:
            log_message("✅ Aucune permission spéciale — application basique")

        # Vérifier que les permissions d'exécution sont bien gérées dans le code
        missing_runtime = check_runtime_permissions_in_code(LOCAL_PROJECT_DIR, runtime_perms)
        if missing_runtime:
            log_message(f"🚨 Permissions d'exécution non gérées dans le code: {', '.join(sorted(missing_runtime))}", is_error=True)

        if issues or warnings or missing_runtime:
            if not display_permission_help(issues, warnings, missing_runtime):
                log_message("❌ Compilation annulée — permissions d'exécution manquantes dans le code", is_error=True)
                save_build_summary(time.time() - START_TIME, success=False)
                return 1
        log_message("")

        # Étape 2: Se connecter à la VM
        log_message("ÉTAPE 2: Connexion à la VM")
        log_message("Assurez-vous d'être connecté au VPN de l'école!")
        client = connect_to_vm()
        if not client:
            save_build_summary(time.time() - START_TIME, success=False)
            return 1
        log_message("")

        # Étape 2b: Détecter le SDK/NDK sur la VM
        log_message("ÉTAPE 2b: Détection du SDK/NDK Android sur la VM")
        sdk_path, ndk_path = detect_sdk_ndk_paths(client)
        log_message("")

        # Étape 3: Créer buildozer.spec
        log_message("ÉTAPE 3: Création du fichier buildozer.spec")
        spec_path = create_buildozer_spec(auto_permissions, sdk_path=sdk_path, ndk_path=ndk_path)
        log_message("")

        # Étape 4: Vérifier l'espace disque
        log_message("ÉTAPE 4: Vérification de l'espace disque")
        if not check_and_manage_disk_space(client):
            client.close()
            log_message("❌ Espace disque insuffisant - compilation annulée", is_error=True)
            save_build_summary(time.time() - START_TIME, success=False)
            return 1

        # Étape 5: Transférer les fichiers
        log_message("ÉTAPE 5: Transfert des fichiers")
        remote_dir = transfer_files_to_vm(client)
        if not remote_dir:
            client.close()
            save_build_summary(time.time() - START_TIME, success=False)
            return 1
        log_message("")

        # Étape 6: Vérifier les packages Python
        log_message("ÉTAPE 6: Vérification des packages Python")
        check_and_install_missing_packages(client, remote_dir)
        log_message("")

        # Étape 7: Compiler l'APK
        log_message("ÉTAPE 7: Compilation de l'APK")
        apk_path, build_time = build_apk(client, remote_dir)
        if not apk_path:
            client.close()
            save_build_summary(time.time() - START_TIME, success=False)
            return 1
        log_message("")

        # Étape 8: Télécharger l'APK
        log_message("ÉTAPE 8: Téléchargement de l'APK")
        local_apk = download_apk(client, apk_path)
        if not local_apk:
            client.close()
            save_build_summary(time.time() - START_TIME, success=False)
            return 1
        log_message("")

        client.close()
        log_message("Connexion fermée\n")

        # Étape 9: Installation sur tablette (optionnel)
        log_message("ÉTAPE 9: Installation sur tablette Android (optionnel)")
        install_and_launch_on_device(local_apk, APP_PACKAGE)

        total_time = time.time() - START_TIME
        save_build_summary(total_time, success=True, apk_path=local_apk)

        print("\n" + "=" * 70)
        print("✅ PROCESSUS TERMINÉ AVEC SUCCÈS!")
        print("=" * 70)
        print(f"📦 Fichier APK: {local_apk}")
        print(f"⏱️  Temps total: {total_time/60:.1f} minutes")
        print(f"📄 Log détaillé: {LOG_FILE}")
        print("=" * 70 + "\n", flush=True)
        return 0

    except KeyboardInterrupt:
        log_message("\nProcessus interrompu par l'utilisateur", is_error=True)
        save_build_summary(time.time() - START_TIME, success=False)
        return 1

    except Exception as e:
        log_message(f"Erreur critique: {e}", is_error=True)
        import traceback
        log_message(traceback.format_exc(), is_error=True)
        save_build_summary(time.time() - START_TIME, success=False)
        return 1


# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

if __name__ == "__main__":
    exit_code = main()

    if exit_code == 0:
        print("\n✅ Compilation réussie!")
    else:
        print(f"\n❌ Erreur! Consultez le log pour plus de détails:")
        print(f"   {LOG_FILE}")

    print("\nAppuyez sur Entrée pour fermer...", flush=True)
    try:
        input()
    except Exception:
        pass
