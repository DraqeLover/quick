import asyncio 
from dotenv import load_dotenv 
from deepgram import (  
    DeepgramClient,    
    LiveTranscriptionEvents,  
    LiveOptions, 
    Microphone, 
    SpeakOptions,
)
from google import genai  
from Characters import BDSM, WAR, CRACK, NOGO, FRIGGA, FRIDA
import os
import time
from mutagen.wave import WAVE
import wave
import pyaudio 
import serial 
from wavplayer import play_audio_file

# Load environment variables
load_dotenv("api/Key.env")

# Api key setup
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GEMINI_API_KEY = os.getenv("GENAI_API_KEY")

# Global variables
text = ""
sleep = True
persona = BDSM
dp_voice = "aura-luna-en"
microphone = None
context = ""  # New variable to store conversation history

commands = ""
arduino = serial.Serial(port="COM5", baudrate=9600, timeout=1)
time.sleep(2)  # Wait for connection to establish

# PINDSVIND OUTGOING

async def send_command():
    global commands
    command_str = "".join(commands)  # Convert list to a space-separated string

    # Check if Arduino is connected
    if arduino.is_open:
        arduino.write((command_str + "\n").encode())  # Send command string
        await asyncio.sleep(1)  # Use await with asyncio.sleep()

        response = arduino.readline().decode().strip()  # Read response
        print("Arduino:", response)
        print("Python:", command_str)
    else:
        print("Arduino is not connected or communication error.")

class TranscriptCollector:
    def __init__(self):
        self.reset()

    def reset(self):
        self.transcript_parts = []

    def add_part(self, part):
        self.transcript_parts.append(part)

    def get_full_transcript(self):
        return ' '.join(self.transcript_parts).strip()

transcript_collector = TranscriptCollector()

# Gemini setup
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def generate_message(prompt):
    global context
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",
        contents= persona + prompt + NOGO + "this is the conversation so far: " + context
    )
    context += f"User: {prompt}\nAI: {response.text}\n"
    return response.text

def generate_audio(text):
    deepgram = DeepgramClient(DEEPGRAM_API_KEY)
    options = SpeakOptions(
        model=dp_voice,
        encoding="linear16",
        sample_rate=16000
    )
    response = deepgram.speak.v("2").save("response.wav", {"text": text}, options)

def play_audio():
    try:
        wf = wave.open("response.wav", "rb")
        pa = pyaudio.PyAudio()
        
        stream = pa.open(
            format=pa.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )

        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)

        stream.stop_stream()
        stream.close()
        pa.terminate()
        wf.close()

    except Exception as e:
        print(f"Error playing file: {e}")
        return None

def delete_audio():
    try:
        audio = WAVE("response.wav")
        length = audio.info.length
        print(length)
        os.remove("response.wav")
        print(f"Deleted: response.wav")
    except Exception as e:
        print(f"Error deleting file: {e}")

async def process_transcript(full_sentence, dg_connection):
    global sleep
    global persona
    global dp_voice
    global microphone
    global context
    global commands

    if not full_sentence:
        return

    print(f"speaker: {full_sentence}")

    if sleep:
        if "hey" and "frigga" in full_sentence.lower():
            print("Frigga Detected!")
            commands = "active"
            await send_command()
            persona = FRIGGA
            dp_voice = "aura-asteria-en"
            sleep = False
            transcript_collector.reset()
            return  # Stop processing
        elif "hey" and "crack" in full_sentence.lower():
            print("Crack Detected!")
            persona = CRACK
            dp_voice = "aura-orion-en"
            sleep = False
            transcript_collector.reset()
            return  # Stop processing
        elif "hey" and "frida" in full_sentence.lower():
            print("Frida Detected!")
            persona = FRIDA
            dp_voice = "aura-luna-en"
            sleep = False
            transcript_collector.reset()
            return  # Stop processing
        else:
            transcript_collector.reset()
            return  # Ignore all other speech while sleeping
    else:
        if "bye" in full_sentence.lower():
            print("Goodbye!")
            commands = "none"
            await send_command()
            sleep = True
            process_transcript()
            context = ""
        if "shakira" in full_sentence.lower():
            print("shakira is going hard")
            play_audio_file("Shakira.wav")

        microphone.finish()
        asyncio.create_task(dg_connection.finish())  # Non-blocking stop

        response_text = generate_message(full_sentence)
        print(f"Gemini: {response_text}")
        asyncio.sleep(1.5)
        generate_audio(response_text)
        play_audio()
        delete_audio()
        transcript_collector.reset()

        # Restart in listening mode
        asyncio.create_task(get_transcript())  # Properly restart transcript collection


async def get_transcript():
    global microphone
    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        dg_connection = deepgram.listen.asynclive.v("1")
        microphone = Microphone(dg_connection.send)

        async def on_message(self, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            
            # Ignore empty or very short utterances
            if len(sentence.strip()) < 2:
                return
                
            if not result.speech_final:
                transcript_collector.add_part(sentence)
            else:
                transcript_collector.add_part(sentence)
                full_sentence = transcript_collector.get_full_transcript()
                await process_transcript(full_sentence, dg_connection)

        async def on_error(self, error, **kwargs):
            print(f"\n\n{error}\n\n")

        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        options = LiveOptions(
            model="nova-2",
            punctuate=True,
            language="en-US",
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            endpointing=True
        )

        await dg_connection.start(options)
        microphone.start()

        while True:
            await asyncio.sleep(1)

    except Exception as e:
        print(f"Could not open socket: {e}")
        # Attempt to restart after error
        await asyncio.sleep(5)
        await get_transcript()

if __name__ == "__main__":
    asyncio.run(get_transcript())
