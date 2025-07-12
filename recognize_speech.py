import speech_recognition as sr
import threading
import time

class SpeechRecognizer:
    def __init__(self, parent=None, callback=None):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.parent = parent
        self.callback = callback
        self.is_listening = False
        self.listener_thread = None
        self.stop_listening = False

        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def toggle_listening(self):
        if self.is_listening:
            self.stop_listening = True
            self.is_listening = False
            return False
        else:
            self.stop_listening = False
            self.is_listening = True
            self.listener_thread = threading.Thread(target=self._listen_in_background)
            self.listener_thread.daemon = True
            self.listener_thread.start()
            return True

    def _listen_in_background(self):
        while self.is_listening and not self.stop_listening:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)

                try:
                    recognized_text = self.recognizer.recognize_google(audio)
                    print(f"Recognized: {recognized_text}")

                    if self.callback:
                        self.callback(recognized_text)

                except sr.UnknownValueError:
                    print("Speech Recognition could not understand audio")
                except sr.RequestError as e:
                    print(f"Could not request results from service; {e}")

            except Exception as e:
                print(f"Error in speech recognition: {e}")
                time.sleep(0.5)

        self.is_listening = False
        print("Stopped listening")

    def stop(self):
        self.stop_listening = True
        self.is_listening = False
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(2)