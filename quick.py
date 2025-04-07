import asyncio
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
    SpeakOptions
)
from google import genai
from Characters import BDSM, WAR, CRACK, NOGO, FRIGGA
import os
import subprocess
import pyaudio
import wave

# Linux-specific audio control
def mute_mic():
    subprocess.run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1"])

def unmute_mic():
    subprocess.run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "0"])

load_dotenv("Key.env")

class AudioManager:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = None

    def play_wav(self, filename):
        try:
            wf = wave.open(filename, 'rb')
            self.stream = self.pa.open(
                format=self.pa.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )
            data = wf.readframes(1024)
            while data:
                self.stream.write(data)
                data = wf.readframes(1024)
            wf.close()
        except Exception as e:
            print(f"Playback error: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()

    def cleanup(self):
        self.pa.terminate()

class LinuxAssistant:
    def __init__(self):
        self.audio = AudioManager()
        self.dg_client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
        self.gemini = genai.Client(api_key=os.getenv("GENAI_API_KEY"))
        self.transcript = []
        self.sleep = True
        self.persona = BDSM
        self.voice = "aura-luna-en"
        self.mic = None
        self.connection = None

    async def process_command(self, text):
        if not text:
            return

        print(f"User: {text}")

        if self.sleep:
            if "hey frigga" in text.lower():
                self.wake_up(FRIGGA, "aura-asteria-en")
            elif "hey crack" in text.lower():
                self.wake_up(CRACK, "aura-orion-en")
            return

        if "bye" in text.lower():
            self.sleep = True
            return

        await self.respond_to_query(text)

    def wake_up(self, persona, voice):
        print("Wake word detected!")
        self.persona = persona
        self.voice = voice
        self.sleep = False
        self.transcript = []

    async def respond_to_query(self, query):
        # Mute mic before processing
        mute_mic()
        
        # Stop current listening session
        if self.mic:
            self.mic.finish()
        if self.connection:
            await self.connection.finish()

        # Generate and play response
        response = self.generate_response(query)
        print(f"Assistant: {response}")
        self.generate_audio(response)
        self.audio.play_wav("response.wav")
        os.remove("response.wav")

        # Restart listening
        unmute_mic()
        await self.start_listening()

    def generate_response(self, prompt):
        return self.gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=self.persona + prompt + NOGO
        ).text

    def generate_audio(self, text):
        self.dg_client.speak.v("2").save(
            "response.wav",
            {"text": text},
            SpeakOptions(
                model=self.voice,
                encoding="linear16",
                sample_rate=16000
            )
        )

    async def start_listening(self):
        self.connection = self.dg_client.listen.asynclive.v("1")
        self.mic = Microphone(self.connection.send)

        async def on_message(_, result, **__):
            text = result.channel.alternatives[0].transcript
            if not text.strip():
                return

            if result.speech_final:
                self.transcript.append(text)
                await self.process_command(' '.join(self.transcript))
                self.transcript = []
            else:
                self.transcript.append(text)

        self.connection.on(LiveTranscriptionEvents.Transcript, on_message)
        await self.connection.start(LiveOptions(
            model="nova-2",
            punctuate=True,
            language="en-US",
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            endpointing=True
        ))
        self.mic.start()

    async def run(self):
        try:
            await self.start_listening()
            while True:
                await asyncio.sleep(1)
        finally:
            self.audio.cleanup()
            if self.mic:
                self.mic.finish()
            if self.connection:
                await self.connection.finish()

if __name__ == "__main__":
    assistant = LinuxAssistant()
    try:
        asyncio.run(assistant.run())
    except KeyboardInterrupt:
        print("\nExiting...")
