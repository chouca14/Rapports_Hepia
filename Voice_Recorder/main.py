# -----------------------------------------------------------------------------
# Author      : Guilhem Rozier Vilardell
# Last edited : 2025-06-16
# Description : Android voice recorder app using native SpeechRecognizer and
#               Gemini 2.5 Flash for transcription summarization.
# -----------------------------------------------------------------------------

import threading
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.clock import mainthread

# On Android the 'android' module exists; on PC it does not.
# This allows the code to run on both platforms.
try:
    from android.permissions import request_permissions, Permission
    ANDROID = True
except ImportError:
    ANDROID = False

# --- Constants ----------------------------------------------------------------
GEMINI_API_KEY = "AIzaSyALYJUs_u7HUHdO2HbIA1MYB9NWXpCAFuw"
GEMINI_URL     = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)
RECOGNITION_LANGUAGE = "fr-FR"

ERROR_MESSAGES = {
    1: "network error",
    2: "network error",
    3: "audio error",
    4: "server error",
    5: "client error",
    6: "no speech detected",
    7: "timeout",
    8: "speech too short",
    9: "missing permission",
}


# --- Gemini API ---------------------------------------------------------------

def build_gemini_body(text):
    """
    Build the JSON body for the Gemini API request.
    :param text: transcribed text to summarize
    :return: dict formatted as required by the Gemini API
    """
    prompt = (
        "Summarize this text in French in a few clear sentences, "
        "then list the keywords. Correct phonetically close but "
        f"misrecognized words (e.g. 'vin' → '20'):\n\n{text}"
    )
    return {"contents": [{"parts": [{"text": prompt}]}]}


def parse_gemini_response(data):
    """
    Extract the text content from a Gemini API response.
    :param data: parsed JSON response dict from the Gemini API
    :return: summary string, or error string if response is malformed
    """
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        return f"(invalid response: {e})"


def get_summary(text):
    """
    Send transcribed text to Gemini API and return a summary with keywords.
    :param text: transcribed text to summarize
    :return: summary string, or error string on failure
    """
    import requests
    try:
        response = requests.post(GEMINI_URL, json=build_gemini_body(text), timeout=30)
        return parse_gemini_response(response.json())
    except Exception as e:
        return f"(summary error: {e})"


# --- Main screen --------------------------------------------------------------

class MainScreen(Screen):

    def on_enter(self):
        """
        Request microphone and internet permissions when the screen becomes visible.
        Required on Android 6+ for runtime permission handling.
        """
        if ANDROID:
            request_permissions([Permission.RECORD_AUDIO, Permission.INTERNET])

    def start_recording(self):
        """
        Start Android native speech recognition.
        On PC, falls back to a simulation message.
        """
        self._set_ui_recording_state()

        if not ANDROID:
            self._on_result("(PC simulation: recognition unavailable)")
            return

        self._launch_speech_recognizer()

    def summarize(self):
        """
        Send current transcription to Gemini in a background thread.
        Does nothing if transcription is empty or an error message.
        """
        text = self.ids.label_transcription.text
        if not text or text.startswith("("):
            return

        self.ids.label_status.text      = "Summarizing..."
        self.ids.btn_summarize.disabled = True

        # get_summary() blocks on HTTP — run in background thread to keep UI responsive.
        # daemon=True: thread is killed automatically when the app closes.
        threading.Thread(
            target=lambda: self._on_summary(get_summary(text)),
            daemon=True
        ).start()

    def _set_ui_recording_state(self):
        """
        Reset UI to recording state: clear labels, disable buttons.
        """
        self.ids.label_status.text        = "Speak now..."
        self.ids.label_transcription.text = ""
        self.ids.label_summary.text       = ""
        self.ids.btn_start.disabled       = True
        self.ids.btn_summarize.disabled   = True

    def _launch_speech_recognizer(self):
        """
        Create and start an Android SpeechRecognizer on the UI thread.

        SpeechRecognizer must be created on the Android UI thread (Android constraint).
        pyjnius is used to bridge Python objects to Java interfaces required by Android.

        Note: Listener and StartRunnable are defined as inner classes here (not at module
        level) because they need closure access to 'activity' and 'screen'. This is a
        known pyjnius pattern and is intentional.
        """
        from jnius import autoclass, PythonJavaClass, java_method

        SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
        RecognizerIntent = autoclass("android.speech.RecognizerIntent")
        Intent           = autoclass("android.content.Intent")
        PythonActivity   = autoclass("org.kivy.android.PythonActivity")
        activity         = PythonActivity.mActivity
        screen           = self

        class Listener(PythonJavaClass):
            # Tells pyjnius this Python object implements the Java RecognitionListener interface.
            # Android will call these methods when recognition events occur.
            __javainterfaces__ = ["android/speech/RecognitionListener"]
            # Binds the object to the app classloader — required by pyjnius, else crash.
            __javacontext__    = "app"

            # Signature format: "(argument_types)return_type" in JVM bytecode notation.
            # L = object, V = void, I = int, F = float, [B = byte[], ; ends object type.

            @java_method("(Landroid/os/Bundle;)V")
            def onResults(self, results):
                # Android passes a Bundle with key "results_recognition" = list of
                # recognized strings sorted by confidence. Index 0 = best result.
                matches = results.getStringArrayList("results_recognition")
                text = matches.get(0) if matches and matches.size() > 0 else "(no result)"
                screen._on_result(text)

            @java_method("(I)V")
            def onError(self, error):
                msg = ERROR_MESSAGES.get(error, f"unknown error {error}")
                screen._on_result(f"(error: {msg})")

            # The following methods are required by the RecognitionListener interface
            # but are not used in this application.
            @java_method("(Landroid/os/Bundle;)V")
            def onReadyForSpeech(self, p): pass

            @java_method("([B)V")
            def onBufferReceived(self, b): pass

            @java_method("(F)V")
            def onRmsChanged(self, r): pass

            @java_method("()V")
            def onEndOfSpeech(self): pass

            @java_method("(Landroid/os/Bundle;)V")
            def onPartialResults(self, r): pass

            @java_method("(ILandroid/os/Bundle;)V")
            def onEvent(self, t, p): pass

            @java_method("()V")
            def onBeginningOfSpeech(self): pass

        # Keep a reference on self to prevent Python GC from destroying the object - MEMORY
        # while Android still holds a pointer to it.
        self._listener = Listener()
        listener       = self._listener

        class StartRunnable(PythonJavaClass):
            # Runnable interface: Android calls run() on the UI thread.
            __javainterfaces__ = ["java/lang/Runnable"]
            __javacontext__    = "app"

            @java_method("()V")
            def run(self):
                rec = SpeechRecognizer.createSpeechRecognizer(activity)
                rec.setRecognitionListener(listener)

                intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, RECOGNITION_LANGUAGE)
                intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)

                rec.startListening(intent)

        activity.runOnUiThread(StartRunnable())

    @mainthread
    def _on_result(self, text):
        """
        Update UI with recognition result. Must run on Kivy main thread.
        :param text: recognized text, or error string starting with '('
        """
        self.ids.label_transcription.text = text
        self.ids.label_status.text        = "Ready"
        self.ids.btn_start.disabled       = False
        self.ids.btn_summarize.disabled   = text.startswith("(")

    @mainthread
    def _on_summary(self, result):
        """
        Update UI with Gemini summary. Must run on Kivy main thread.
        :param result: summary string returned by get_summary()
        """
        self.ids.label_summary.text     = result
        self.ids.label_status.text      = "Ready"
        self.ids.btn_summarize.disabled = False


# --- App entry point ----------------------------------------------------------

class VoiceRecorderApp(App):
    def build(self):
        return MainScreen()


if __name__ == "__main__":
    VoiceRecorderApp().run()