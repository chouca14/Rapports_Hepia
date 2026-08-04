# Voice Recorder

Application Python-Kivy d'enregistrement, transcription et résumé de réunions.

## Fonctionnalités
- Enregistrement audio (WAV)
- Transcription via Google Speech-to-Text (`speech_recognition`)
- Résumé automatique via l'API Google Gemini 2.5 Flash
- Export Markdown (si possible)
- Historique (si possible)

## Installation (Windows)

```bash
python -m venv .venv313
.venv313\Scripts\activate
pip install -r requirements.txt
```

## Structure

```
Voice_Recorder/
main.py
voicerecorder.kv
requirements.txt
config.env   -- clé API
src/
    screens/        -- MainScreen, Possible implémentation: HistoryScreen, TranscriptScreen
    services/       -- audio, transcription, summary
    utils/          -- config
```

## Sources
- https://python-sounddevice.readthedocs.io/en/0.5.3/
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.wavfile.read.html
- https://pypi.org/project/SpeechRecognition/
- https://kivy.org/doc/stable/api-kivy.uix.screenmanager.html

## Auteur
Guilhem Rozier Vilardell, MT2 HEPIA / HES-SO, 2026
