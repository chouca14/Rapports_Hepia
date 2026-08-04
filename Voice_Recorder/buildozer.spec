[app]

# (str) Titre de votre application
title = Voice_Recorder

# (str) Nom du package
package.name = amc

# (str) Domaine du package (unique)
package.domain = org.hepia

# (str) Répertoire source de l'application
source.dir = .

# (list) Fichiers ou répertoires sources à inclure
source.include_exts = py,kv,spec

# (str) Version de l'application
version = 1.0.0

# (list) Dépendances de l'application
# plyer toujours inclus — requis pour accéléromètre, GPS, vibration, etc.
requirements = python3,kivy,plyer,kivy_garden.graph

# (str) Permissions Android
android.permissions = INTERNET, RECORD_AUDIO

# (int) Version du SDK Android cible
android.api = 31

# (int) Version minimale du SDK Android
# IMPORTANT: valeur minimale 24 avec NDK r25b — en dessous, grpmodule.c
# échoue à compiler (setgrent/getgrent absents de l'API Android < 24)
android.minapi = 24

# (int) Version du NDK Android
android.ndk = 25b

# Chemin vers le SDK Android déjà installé (évite le re-téléchargement)
android.sdk_path = /home/student/.buildozer/android/platform/android-sdk
# Chemin vers le NDK Android déjà installé (évite le re-téléchargement)
android.ndk_path = /home/student/.buildozer/android/platform/android-ndk-r25b

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
