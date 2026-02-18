"""
🔄 Système de mise à jour automatique de Jarvis
Ce fichier vérifie toutes les 30 minutes si une nouvelle version est disponible sur GitHub.
"""

import requests
import threading
import time
import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

# ============================================================
# ⚙️ CONFIG - METS TON LIEN GITHUB ICI
# ============================================================
GITHUB_USER     = "Zaplpb"
GITHUB_REPO     = "jarvis-uptades"
FICHIER_JARVIS  = Path(__file__).parent / "jarvis_stable.py"
FICHIER_VERSION = Path(__file__).parent / "jarvis_version.json"
INTERVALLE      = 30 * 60  # Vérification toutes les 30 minutes

# URL du fichier Jarvis sur GitHub
URL_JARVIS  = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/jarvis_stable.py"
URL_VERSION = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.json"

# ============================================================
# 🔧 FONCTIONS
# ============================================================

def get_version_locale():
    """Récupère la version actuelle de Jarvis."""
    try:
        if FICHIER_VERSION.exists():
            data = json.loads(FICHIER_VERSION.read_text(encoding="utf-8"))
            return data.get("version", "0.0.0")
    except:
        pass
    return "0.0.0"

def get_version_github():
    """Récupère la version disponible sur GitHub."""
    try:
        response = requests.get(URL_VERSION, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("version", "0.0.0")
    except:
        pass
    return None

def telecharger_mise_a_jour():
    """Télécharge le nouveau fichier Jarvis depuis GitHub."""
    try:
        response = requests.get(URL_JARVIS, timeout=30)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"[UPDATE] Erreur téléchargement : {e}")
    return None

def tester_code(code):
    """Vérifie que le code est valide avant de l'installer."""
    try:
        compile(code, "<string>", "exec")
        return True
    except SyntaxError as e:
        print(f"[UPDATE] ❌ Erreur dans le code : {e}")
        return False

def sauvegarder_backup():
    """Sauvegarde l'ancienne version de Jarvis."""
    try:
        backup = Path(__file__).parent / "jarvis_backup.py"
        backup.write_text(FICHIER_JARVIS.read_text(encoding="utf-8"), encoding="utf-8")
        print("[UPDATE] ✅ Backup sauvegardé")
        return True
    except Exception as e:
        print(f"[UPDATE] ❌ Erreur backup : {e}")
        return False

def installer_mise_a_jour(code, nouvelle_version):
    """Installe la nouvelle version de Jarvis."""
    try:
        # Sauvegarder l'ancienne version
        if not sauvegarder_backup():
            return False

        # Écrire le nouveau fichier
        FICHIER_JARVIS.write_text(code, encoding="utf-8")

        # Mettre à jour la version locale
        FICHIER_VERSION.write_text(
            json.dumps({"version": nouvelle_version, "date": str(datetime.now())},
                      ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"[UPDATE] ✅ Mise à jour {nouvelle_version} installée !")
        return True

    except Exception as e:
        print(f"[UPDATE] ❌ Erreur installation : {e}")
        # Restaurer le backup en cas d'erreur
        try:
            backup = Path(__file__).parent / "jarvis_backup.py"
            if backup.exists():
                FICHIER_JARVIS.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
                print("[UPDATE] ✅ Ancienne version restaurée")
        except:
            pass
        return False

def verifier_mise_a_jour(parler_func=None):
    """Vérifie si une mise à jour est disponible et l'installe si oui."""
    print(f"[UPDATE] 🔍 Vérification des mises à jour...")

    version_locale    = get_version_locale()
    version_github    = get_version_github()

    if version_github is None:
        print("[UPDATE] ⚠️ Impossible de contacter GitHub")
        return

    print(f"[UPDATE] Version locale : {version_locale} | GitHub : {version_github}")

    if version_github <= version_locale:
        print("[UPDATE] ✅ Jarvis est à jour !")
        return

    # Nouvelle version disponible !
    print(f"[UPDATE] 🆕 Nouvelle version {version_github} disponible !")

    if parler_func:
        parler_func(f"Mise à jour version {version_github} disponible, installation en cours.")

    # Télécharger
    nouveau_code = telecharger_mise_a_jour()
    if not nouveau_code:
        if parler_func:
            parler_func("Échec du téléchargement de la mise à jour.")
        return

    # Tester le code
    if not tester_code(nouveau_code):
        if parler_func:
            parler_func("La mise à jour contient des erreurs, j'ai gardé l'ancienne version.")
        return

    # Installer
    if installer_mise_a_jour(nouveau_code, version_github):
        if parler_func:
            parler_func(f"Mise à jour version {version_github} installée avec succès ! Je redémarre.")
        time.sleep(2)
        # Redémarrer Jarvis
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        if parler_func:
            parler_func("Échec de l'installation, j'ai gardé l'ancienne version.")

def boucle_mise_a_jour(parler_func=None):
    """Boucle infinie qui vérifie les mises à jour régulièrement."""
    while True:
        try:
            verifier_mise_a_jour(parler_func)
        except Exception as e:
            print(f"[UPDATE] Erreur : {e}")
        time.sleep(INTERVALLE)

def demarrer_updater(parler_func=None):
    """Lance le système de mise à jour en arrière-plan."""
    print("[UPDATE] 🚀 Système de mise à jour démarré")
    thread = threading.Thread(
        target=boucle_mise_a_jour,
        args=(parler_func,),
        daemon=True
    )
    thread.start()
