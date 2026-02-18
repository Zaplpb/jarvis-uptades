import threading
from updater import demarrer_updater
import time
import os
import re
import json
import webbrowser
import subprocess
import urllib.parse
import requests
import pyautogui
import speech_recognition as sr
import pyttsx3
from datetime import datetime, timedelta
from pathlib import Path

# ==========================
# CONFIGURATION
# ==========================
MICRO_NUM      = 1
VILLE          = "Avignon"
METEO_API_KEY  = "8f06012f97d6452d63b0be6ada8629ec"
MAX_HISTORIQUE = 10
STYLE_REPONSE  = "court"

# ==========================
# AUTO-APPRENTISSAGE
# ==========================
FICHIER_APPRENTISSAGE = Path(__file__).parent / "jarvis_apprentissage.json"

def _charger_apprentissage():
    try:
        if FICHIER_APPRENTISSAGE.exists():
            data = json.loads(FICHIER_APPRENTISSAGE.read_text(encoding="utf-8"))
            return data.get("corrections", {}), data.get("commandes", {})
    except:
        pass
    return {}, {}

def _sauvegarder_apprentissage(corrections, commandes):
    try:
        FICHIER_APPRENTISSAGE.write_text(
            json.dumps({"corrections": corrections, "commandes": commandes},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
    except Exception as e:
        print(f"[APPRENTISSAGE] Erreur sauvegarde : {e}")

_corrections_apprises, _commandes_apprises = _charger_apprentissage()

# ==========================
# APPLICATIONS / SITES
# ==========================
APPLICATIONS = {
    "discord":      r"C:\Users\zap\AppData\Local\Discord\Update.exe",
    "steam":        r"C:\Program Files (x86)\Steam\Steam.exe",
    "spotify":      r"C:\Users\zap\AppData\Roaming\Spotify\Spotify.exe",
    "zen":          r"C:\Program Files\Zen Browser\zen.exe",
    "navigateur":   r"C:\Program Files\Zen Browser\zen.exe",
    "notepad":      r"notepad.exe",
    "calculatrice": r"calc.exe",
    "explorateur":  r"explorer.exe",
    "vscode":       r"C:\Users\zap\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "obs":          r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
    "vlc":          r"C:\Program Files\VideoLAN\VLC\vlc.exe",
}
PROCESSUS = {
    "steam": "steam.exe", "discord": "Discord.exe", "spotify": "Spotify.exe",
    "zen": "zen.exe", "navigateur": "zen.exe", "notepad": "notepad.exe",
    "calculatrice": "Calculator.exe", "explorateur": "explorer.exe",
    "vscode": "Code.exe", "obs": "obs64.exe", "vlc": "vlc.exe",
}
SITES = {
    "youtube":   "https://www.youtube.com",
    "google":    "https://www.google.com",
    "twitch":    "https://www.twitch.tv",
    "netflix":   "https://www.netflix.com",
    "github":    "https://www.github.com",
    "twitter":   "https://www.twitter.com",
    "reddit":    "https://www.reddit.com",
    "wikipedia": "https://www.wikipedia.org",
    "amazon":    "https://www.amazon.fr",
    "leboncoin": "https://www.leboncoin.fr",
    "chatgpt":   "https://chat.openai.com",
}
ZEN_EXE = r"C:\Program Files\Zen Browser\zen.exe"
VARIANTES_DISCORD = ["discord","discird","discorde","discor","discore","discod"]

# ==========================
# CORRECTIONS PRONONCIATION
# ==========================
CORRECTIONS = {
    "jarvi": "jarvis", "jarvist": "jarvis", "jarve": "jarvis",
    "j'arvis": "jarvis", "j'arvi": "jarvis", "jarbi": "jarvis",
    "spotif": "spotify", "spoti": "spotify", "spotefi": "spotify",
    "discor": "discord", "discorde": "discord", "discore": "discord",
    "stim": "steam", "steem": "steam",
    "yutub": "youtube", "utube": "youtube", "youtub": "youtube",
    "fermt": "ferme", "ferm": "ferme",
    "lonse": "lance", "lanse": "lance",
    "ouv": "ouvre", "ouvr": "ouvre",
    "por": "pause", "pauze": "pause",
    "soivant": "suivant",
    "meteo": "météo", "meto": "météo",
    "leure": "heure", "l'heure": "heure",
}

def corriger_commande(texte):
    toutes = {**CORRECTIONS, **_corrections_apprises}
    mots = texte.lower().split()
    corriges = []
    for mot in mots:
        if mot in toutes:
            corriges.append(toutes[mot])
        else:
            trouve = False
            for variante, correct in toutes.items():
                if variante in mot and len(variante) > 4:
                    corriges.append(mot.replace(variante, correct))
                    trouve = True
                    break
            if not trouve:
                corriges.append(mot)
    return " ".join(corriges)

# ==========================
# ÉTAT GLOBAL
# ==========================
ecoute_active  = True
ecoute_bloquee = False
historique     = []

# ==========================
# SYSTÈME DE VOIX — MINIMALISTE
# ==========================
_est_en_train_de_parler = False
_verrou_voix = threading.Lock()

def parler(texte):
    global _est_en_train_de_parler, ecoute_bloquee
    if not texte or not texte.strip():
        return
    with _verrou_voix:
        moteur = None
        try:
            _est_en_train_de_parler = True
            ecoute_bloquee = True
            moteur = pyttsx3.init()
            moteur.setProperty('rate', 175)
            moteur.setProperty('volume', 1.0)
            for v in moteur.getProperty('voices'):
                if 'fr' in v.id.lower() or 'french' in v.name.lower():
                    moteur.setProperty('voice', v.id)
                    break
            moteur.say(texte)
            moteur.runAndWait()
        except Exception as e:
            print(f"[VOIX] Erreur : {e}")
        finally:
            try:
                if moteur:
                    moteur.stop()
            except:
                pass
            _est_en_train_de_parler = False
            ecoute_bloquee = False

def stopper_parole():
    global _est_en_train_de_parler, ecoute_bloquee
    _est_en_train_de_parler = False
    ecoute_bloquee = False

# ==========================
# HEURE & DATE
# ==========================
def get_heure_date(commande):
    now   = datetime.now()
    jours = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
    mois  = ["janvier","février","mars","avril","mai","juin",
             "juillet","août","septembre","octobre","novembre","décembre"]
    if any(m in commande for m in ["heure","heures","il est","time"]):
        return f"Il est {now.hour} heures {now.minute}."
    if any(m in commande for m in ["date","jour","quel jour","on est"]):
        return f"Nous sommes le {jours[now.weekday()]} {now.day} {mois[now.month-1]}."
    return None

# ==========================
# MÉTÉO
# ==========================
def get_meteo(commande):
    if not any(m in commande for m in ["météo","meteo","temps","température","temp"]):
        return None
    if any(m in commande for m in ["demain","après-demain","semaine","prochaine"]):
        return None
    ville = VILLE
    for mot in commande.split():
        if mot.istitle() and len(mot) > 3:
            ville = mot; break
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={ville}&appid={METEO_API_KEY}&units=metric&lang=fr"
        data = requests.get(url, timeout=5).json()
        if data.get("cod") != 200:
            return f"Je n'ai pas trouvé la météo pour {ville}."
        temp = round(data["main"]["temp"])
        desc = data["weather"][0]["description"]
        return f"À {ville}, il fait {temp} degrés, {desc}."
    except:
        return "Impossible de récupérer la météo."

def get_meteo_previsions(commande):
    if not any(m in commande for m in ["météo","meteo","temps","température"]):
        return None
    if not any(m in commande for m in ["demain","après-demain","semaine","prochaine"]):
        return None
    ville = VILLE
    for mot in commande.split():
        if mot.istitle() and len(mot) > 3:
            ville = mot; break
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={ville}&appid={METEO_API_KEY}&units=metric&lang=fr"
        data = requests.get(url, timeout=5).json()
        if data.get("cod") != "200":
            return f"Je n'ai pas trouvé les prévisions pour {ville}."
        liste = data["list"]
        if "demain" in commande:
            demain = datetime.now() + timedelta(days=1)
            prev = [x for x in liste if datetime.fromtimestamp(x["dt"]).date() == demain.date()]
            if prev:
                temp = round(sum(x["main"]["temp"] for x in prev)/len(prev))
                desc = prev[len(prev)//2]["weather"][0]["description"]
                return f"Demain à {ville}, environ {temp} degrés, {desc}."
        if "après-demain" in commande or "apres-demain" in commande:
            apres = datetime.now() + timedelta(days=2)
            prev = [x for x in liste if datetime.fromtimestamp(x["dt"]).date() == apres.date()]
            if prev:
                temp = round(sum(x["main"]["temp"] for x in prev)/len(prev))
                desc = prev[len(prev)//2]["weather"][0]["description"]
                return f"Après-demain à {ville}, environ {temp} degrés, {desc}."
        return "Prévisions non disponibles pour cette période."
    except:
        return "Impossible de récupérer les prévisions."

# ==========================
# MINUTEUR
# ==========================
def get_minuteur(commande):
    if not any(m in commande for m in ["minuteur","timer","chrono"]):
        return None
    duree = 0
    if "minute" in commande:
        match = re.search(r"(\d+)\s*minute", commande)
        if match: duree = int(match.group(1)) * 60
    if "seconde" in commande:
        match = re.search(r"(\d+)\s*seconde", commande)
        if match: duree += int(match.group(1))
    if "heure" in commande:
        match = re.search(r"(\d+)\s*heure", commande)
        if match: duree = int(match.group(1)) * 3600
    if duree == 0:
        return "Je n'ai pas compris la durée du minuteur."
    def _sonner(d):
        time.sleep(d)
        parler("Minuteur terminé.")
    threading.Thread(target=_sonner, args=(duree,), daemon=True).start()
    min_str = f"{duree//60} minute{'s' if duree//60>1 else ''}" if duree >= 60 else f"{duree} seconde{'s' if duree>1 else ''}"
    return f"Minuteur de {min_str} lancé."

# ==========================
# ALARME
# ==========================
def get_alarme(commande):
    if not any(m in commande for m in ["alarme","réveil","réveille","reveille"]):
        return None
    match = re.search(r"(\d{1,2})\s*h\s*(\d{1,2})?", commande)
    if not match:
        return "Je n'ai pas compris l'heure de l'alarme."
    heure = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    now = datetime.now()
    alarme_time = now.replace(hour=heure, minute=minute, second=0, microsecond=0)
    if alarme_time <= now:
        alarme_time += timedelta(days=1)
    attente = (alarme_time - now).total_seconds()
    def _sonner(d):
        time.sleep(d)
        parler("Alarme ! Il est l'heure de se réveiller.")
    threading.Thread(target=_sonner, args=(attente,), daemon=True).start()
    return f"Alarme réglée pour {heure}h{minute:02d}."

# ==========================
# NOTES
# ==========================
FICHIER_NOTES = Path(__file__).parent / "jarvis_notes.txt"
def gerer_notes(commande):
    if "note" in commande or "mémorise" in commande or "écris" in commande:
        if "lis" in commande or "quelles sont" in commande:
            try:
                if FICHIER_NOTES.exists():
                    notes = FICHIER_NOTES.read_text(encoding="utf-8").strip()
                    if notes:
                        return f"Vos notes : {notes}"
                return "Vous n'avez aucune note."
            except:
                return "Erreur de lecture des notes."
        if "efface" in commande or "supprime" in commande:
            try:
                if FICHIER_NOTES.exists():
                    FICHIER_NOTES.unlink()
                return "Notes effacées."
            except:
                return "Erreur lors de la suppression."
        for mot_cle in ["note que","mémorise","écris que","prends note"]:
            if mot_cle in commande:
                texte = commande.split(mot_cle, 1)[-1].strip()
                if texte:
                    try:
                        with open(FICHIER_NOTES, "a", encoding="utf-8") as f:
                            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} : {texte}\n")
                        return "Note enregistrée."
                    except:
                        return "Erreur lors de l'enregistrement."
    return None

# ==========================
# CAPTURE ÉCRAN
# ==========================
def capture_ecran(commande):
    if any(m in commande for m in ["capture","screenshot","screen"]):
        try:
            fichier = str(Path.home() / "Desktop" / f"capture_{int(time.time())}.png")
            pyautogui.screenshot(fichier)
            return "Capture d'écran enregistrée."
        except:
            return "Erreur lors de la capture."
    return None

# ==========================
# VOLUME SYSTÈME
# ==========================
def controle_volume(commande):
    # Couper / remettre le son
    if any(m in commande for m in ["coupe le son","mute","silence","son coupé"]):
        pyautogui.press("volumemute")
        return None
    if any(m in commande for m in ["remet le son","unmute","réactive le son"]):
        pyautogui.press("volumemute")
        return None

    # Mettre à X% direct : "mets le son à 50" / "monte le son à 100"
    if any(m in commande for m in ["mets le son à","règle le son à","volume à","son à","monte le son à","baisse le son à"]):
        match = re.search(r"(\d+)", commande)
        if match:
            pct = max(0, min(100, int(match.group(1))))
            for _ in range(50): pyautogui.press("volumedown")
            for _ in range(pct // 2): pyautogui.press("volumeup")
            return f"Volume à {pct} pourcent."

    # Monte de X%
    if any(m in commande for m in ["monte le son","plus fort","augmente le son"]):
        match = re.search(r"(\d+)", commande)
        nb = max(1, int(match.group(1)) // 2) if match else 2
        for _ in range(nb): pyautogui.press("volumeup")
        return None

    # Baisse de X%
    if any(m in commande for m in ["baisse le son","moins fort","diminue le son"]):
        match = re.search(r"(\d+)", commande)
        nb = max(1, int(match.group(1)) // 2) if match else 2
        for _ in range(nb): pyautogui.press("volumedown")
        return None

    return None

# ==========================
# MUSIQUE
# ==========================
def controle_musique(commande):
    if any(m in commande for m in ["play","lecture","reprends","lance la musique"]):
        pyautogui.press("playpause"); return None
    if any(m in commande for m in ["pause","mets en pause","stop la musique"]):
        pyautogui.press("playpause"); return None
    if any(m in commande for m in ["suivant","next","chanson suivante","change de titre"]):
        pyautogui.press("nexttrack"); return None
    if any(m in commande for m in ["précédent","precedent","chanson précédente","retour"]):
        pyautogui.press("prevtrack"); return None
    return None

# ==========================
# APPLICATIONS
# ==========================
def lancer_app(commande):
    if not any(m in commande for m in ["lance","ouvre","démarre","demarre","open","start"]):
        return None
    for variante in VARIANTES_DISCORD:
        if variante in commande:
            commande = commande.replace(variante, "discord")
    for app, chemin in APPLICATIONS.items():
        if app in commande:
            try:
                if app == "discord":
                    subprocess.Popen([chemin, "--processStart", "Discord.exe"])
                else:
                    subprocess.Popen([chemin], shell=True)
                return None
            except:
                return f"Impossible de lancer {app}."
    return None

def fermer_app(commande):
    if not any(m in commande for m in ["ferme","quitte","close","kill","stop"]):
        return None
    for variante in VARIANTES_DISCORD:
        if variante in commande:
            commande = commande.replace(variante, "discord")
    for app, proc in PROCESSUS.items():
        if app in commande:
            try:
                subprocess.run(["taskkill", "/F", "/IM", proc], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return None
            except:
                return f"Impossible de fermer {app}."
    for site in SITES.keys():
        if site in commande:
            try:
                subprocess.run(["taskkill", "/F", "/IM", "zen.exe"], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return None
            except:
                pass
    return None

# ==========================
# SITES WEB
# ==========================
def ouvrir_site(commande):
    if not any(m in commande for m in ["ouvre","lance","va sur","open","go"]):
        return None
    for site, url in SITES.items():
        if site in commande:
            try:
                subprocess.Popen([ZEN_EXE, url])
                return None
            except:
                webbrowser.open(url)
                return None
    return None

# ==========================
# RECHERCHES
# ==========================
def chercher_youtube(commande):
    if "cherche sur youtube" in commande or ("youtube" in commande and "cherche" in commande):
        query = commande.split("youtube")[-1].strip()
        for mot in ["cherche","recherche","trouve"]:
            query = query.replace(mot, "").strip()
        if query:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            try:
                subprocess.Popen([ZEN_EXE, url])
            except:
                webbrowser.open(url)
            return f"Je cherche {query} sur YouTube."
    return None

def chercher_google(commande):
    if "cherche sur google" in commande or ("google" in commande and "cherche" in commande):
        query = commande.split("google")[-1].strip()
        for mot in ["cherche","recherche","trouve"]:
            query = query.replace(mot, "").strip()
        if query:
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            try:
                subprocess.Popen([ZEN_EXE, url])
            except:
                webbrowser.open(url)
            return f"Je cherche {query} sur Google."
    # "cherche X" sans préciser youtube/google → Claude IA répond à l'oral
    if any(m in commande for m in ["cherche","recherche","qui est","qu'est-ce que","c'est quoi","infos sur","parle-moi de"]):
        return None  # tombe dans _llm automatiquement
    return None

# ==========================
# CONTRÔLE PC
# ==========================
def controle_pc(commande):
    if any(m in commande for m in ["éteins le pc","shutdown","arrête le pc"]):
        parler("Extinction dans 30 secondes.")
        subprocess.run(["shutdown", "/s", "/t", "30"])
        return None
    if "annule" in commande and "extinction" in commande:
        subprocess.run(["shutdown", "/a"])
        return "Extinction annulée."
    if any(m in commande for m in ["redémarre","reboot","restart"]):
        parler("Redémarrage dans 30 secondes.")
        subprocess.run(["shutdown", "/r", "/t", "30"])
        return None
    if any(m in commande for m in ["verrouille","lock","verrouillage"]):
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return None
    if any(m in commande for m in ["mets en veille","sleep","hibernation"]):
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return None
    return None

# ==========================
# LLM (CLAUDE API)
# ==========================
def _llm(question):
    global historique

    if STYLE_REPONSE == "court":
        system_prompt = ("Tu es Jarvis, un assistant vocal intelligent. "
                        "Réponds TOUJOURS en français, en 1-2 phrases courtes et naturelles. "
                        "Ne pose pas de questions. Ne commence jamais par 'Bien sûr' ou 'Absolument'. "
                        "Va droit au but.")
    else:
        system_prompt = ("Tu es Jarvis, un assistant vocal intelligent. "
                        "Réponds TOUJOURS en français, de façon claire et naturelle. "
                        "Ne pose pas de questions. Va droit au but.")

    historique.append({"role": "user", "content": question})
    if len(historique) > MAX_HISTORIQUE * 2:
        historique = historique[-(MAX_HISTORIQUE * 2):]

    # Construire les messages avec le system prompt intégré
    messages = [{"role": "system", "content": system_prompt}] + historique

    try:
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "mistral",
                "messages": messages,
                "stream": False
            },
            timeout=60
        )
        if resp.status_code == 200:
            data = resp.json()
            reponse = data["message"]["content"].strip()
            historique.append({"role": "assistant", "content": reponse})
            print(f"[LLM] {reponse}")
            return reponse
        else:
            print(f"[LLM] Erreur HTTP {resp.status_code} : {resp.text}")
            return "Désolé, je n'ai pas pu obtenir de réponse."
    except Exception as e:
        print(f"[LLM] Erreur : {e}")
        return "Erreur de connexion à l'IA."

# ==========================
# TRAITEMENT COMMANDE
# ==========================
def traiter_commande(commande):
    commande = commande.lower().strip()

    # Couper la parole immédiatement
    if any(m in commande for m in ["chut","tais-toi","stop","silence","arrête de parler"]):
        stopper_parole()
        return None
    
    for fn in [controle_volume, controle_musique, controle_pc]:
        r = fn(commande)
        if r is not None: return r
    
    for fn in [lancer_app, fermer_app]:
        r = fn(commande)
        if r is not None: return r
    
    r = ouvrir_site(commande)
    if r is not None: return r


    
    for fn in [chercher_youtube, chercher_google, get_heure_date,
               get_meteo_previsions, get_meteo, get_minuteur, get_alarme,
               gerer_notes, capture_ecran]:
        r = fn(commande)
        if r is not None: return r
    
    # Mistral uniquement si "cherche" est dans la commande
    if "cherche" in commande:
        query = commande.replace("cherche", "").strip()
        return _llm(query) if query else None
    return None

# ==========================
# EXÉCUTION — VERSION ULTRA SIMPLE
# ==========================
MOTS_INSTANTANES = [
    "pause","suivant","next","précédent","volume","monte","baisse",
    "coupe","mute","ouvre","lance","ferme","quitte","capture","screenshot",
]

_verrou_exec = threading.Lock()

def executer_commande(commande):
    global ecoute_bloquee
    
    # Vérifier qu'une seule commande s'exécute à la fois
    if not _verrou_exec.acquire(blocking=False):
        print("[EXEC] Ignorée — commande déjà en cours")
        return
    
    try:
        ecoute_bloquee = True
        
        # Pas de "Un instant" — on attend juste la réponse
        
        # Traiter la commande
        reponse = traiter_commande(commande)
        
        # Dire la réponse si elle existe
        if reponse and reponse.strip():
            parler(reponse)
        
        # Attendre que Jarvis ait fini de parler
        while _est_en_train_de_parler:
            time.sleep(0.1)
        time.sleep(0.3)
        
    except Exception as e:
        print(f"[ERREUR] {e}")
    finally:
        ecoute_bloquee = False
        _verrou_exec.release()

# ==========================
# ÉCOUTE INTERRUPTION
# ==========================
def ecouter_interruption():
    r = sr.Recognizer()
    while ecoute_active:
        if not _est_en_train_de_parler:
            time.sleep(0.1)
            continue
        try:
            with sr.Microphone(device_index=MICRO_NUM) as source:
                try: 
                    audio = r.listen(source, timeout=1, phrase_time_limit=2)
                except sr.WaitTimeoutError: 
                    continue
            
            texte = r.recognize_google(audio, language="fr-FR").lower()
            if any(m in texte for m in ["arrete","stop","tais-toi","silence","chut"]):
                stopper_parole()
        except:
            continue

# ==========================
# ÉCOUTE PRINCIPALE
# ==========================
MOTS_JARVIS_PROPRES = [
    "un instant","oui monsieur","bonjour","bonsoir","à bientôt","en veille",
]

def ecouter():
    global ecoute_bloquee
    
    r_wake = sr.Recognizer()
    r_wake.energy_threshold = 1200
    r_wake.dynamic_energy_threshold = False
    r_wake.pause_threshold = 0.5

    r_cmd = sr.Recognizer()
    r_cmd.energy_threshold = 300
    r_cmd.dynamic_energy_threshold = True
    r_cmd.pause_threshold = 1.4

    print("🎙️  Calibration du micro...")
    try:
        with sr.Microphone(device_index=MICRO_NUM) as source:
            r_wake.adjust_for_ambient_noise(source, duration=2)
        r_wake.energy_threshold = max(r_wake.energy_threshold * 1.5, 800)
        print(f"✅ Seuil : {int(r_wake.energy_threshold)}")
    except Exception as e:
        print(f"⚠️  Calibration échouée : {e}")

    print("✅ Jarvis prête.\n")

# 🔄 Démarrer le système de mise à jour automatique
demarrer_updater(parler_func=parler)

    while ecoute_active:
        # Attendre que Jarvis ne parle pas et ne soit pas bloquée
        if ecoute_bloquee or _est_en_train_de_parler:
            time.sleep(0.1)
            continue

        try:
            # Phase 1 : Détecter "Jarvis"
            with sr.Microphone(device_index=MICRO_NUM) as source:
                try: 
                    audio = r_wake.listen(source, timeout=10, phrase_time_limit=3)
                except sr.WaitTimeoutError: 
                    continue

            # Double vérification
            if ecoute_bloquee or _est_en_train_de_parler:
                continue

            texte = r_wake.recognize_google(audio, language="fr-FR").lower()
            
            # Ignorer si c'est Jarvis qui parle elle-même
            if any(m in texte for m in MOTS_JARVIS_PROPRES):
                continue
            
            if "jarvis" not in texte:
                continue

            print(f"[WAKE] Jarvis détecté")
            apres = texte.split("jarvis", 1)[-1].strip()

        except sr.UnknownValueError:
            continue
        except Exception as e:
            print(f"[ERREUR WAKE] {e}")
            continue

        # Phase 2 : Commande directe après "Jarvis"
        if apres and len(apres) > 2:
            if apres.strip() in ["veille","arrêt","arret"]:
                parler("Je me mets en veille.")
                continue
            print(f"[JARVIS] {apres}")
            threading.Thread(target=executer_commande, args=(apres,), daemon=True).start()
            continue

        # Phase 3 : Attendre la commande
        ecoute_bloquee = True
        parler("Oui monsieur.")  # bloquant : attend que le worker ait fini
        time.sleep(0.2)
        ecoute_bloquee = False

        try:
            with sr.Microphone(device_index=MICRO_NUM) as source:
                r_cmd.adjust_for_ambient_noise(source, duration=0.3)
                try: 
                    audio = r_cmd.listen(source, timeout=8, phrase_time_limit=15)
                except sr.WaitTimeoutError: 
                    continue
            
            commande = r_cmd.recognize_google(audio, language="fr-FR").lower()
            commande = corriger_commande(commande)
            print(f"[CMD] {commande}")
            
            if commande.strip() in ["veille","arrêt","arret"]:
                parler("Je me mets en veille.")
                continue
            
            threading.Thread(target=executer_commande, args=(commande,), daemon=True).start()
            
        except sr.UnknownValueError:
            continue
        except Exception as e:
            print(f"[ERREUR CMD] {e}")
            continue

# ==========================
# LANCEMENT
# ==========================
print("╔═══════════════════════════════════════════╗")
print("║      JARVIS V4 SIMPLE — Démarrage         ║")
print("╚═══════════════════════════════════════════╝\n")

import speech_recognition as _sr_check
print("🎙️  Micros disponibles :")
for i, nom in enumerate(_sr_check.Microphone.list_microphone_names()):
    print(f"   [{i}] {nom}")
print()

# Précharger Mistral dans Ollama pour éviter le délai au premier appel
print("⏳ Chargement de Mistral...")
try:
    requests.post("http://localhost:11434/api/chat",
        json={"model": "mistral", "messages": [{"role": "user", "content": "bonjour"}], "stream": False},
        timeout=60)
    print("✅ Mistral prêt.")
except Exception as e:
    print(f"⚠️  Ollama non disponible : {e}")

# Message de bienvenue
_h = datetime.now().hour
parler("Bonjour." if 5 <= _h < 18 else "Bonsoir.")

# Lancer l'écoute principale
threading.Thread(target=ecouter, daemon=True).start()

# Lancer le système d'interruption
threading.Thread(target=ecouter_interruption, daemon=True).start()

print("Commandes console : quit\n")

while ecoute_active:
    try:
        if input().strip().lower() == "quit":
            ecoute_active = False
            parler("À bientôt.")
            time.sleep(3)
            break
    except:
        time.sleep(0.5)
