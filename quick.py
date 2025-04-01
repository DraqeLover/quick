import asyncio 
from dotenv import load_dotenv 
from deepgram import (  
    DeepgramClient,  
    DeepgramClientOptions,  
    LiveTranscriptionEvents,  
    LiveOptions, 
    Microphone, 
    SpeakOptions,
)
from google import genai  
from Characters import BDSM, WAR, CRACK, NOGO
import os
import time
import subprocess
from mutagen.wave import WAVE
import wave
import pyaudio  
import pvporcupine  
import struct  
import serial
import random

# Now, we load secret keys from a file called `.env`.
load_dotenv("api/Key.env")

# Api key setup
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GEMINI_API_KEY = os.getenv("GENAI_API_KEY")
PICO_API_KEY = os.getenv("PICO_API_KEY")

STRING = ["armL", "armR", "head"]

arduino = serial.Serial(port="COM3", baudrate=9600, timeout=1)
time.sleep(2)  # Wait for connection to establish

# empty text variable
text = ""

# This is a variable to keep track of whether the program is active or not.
# When it's `True`, the program is listening and responding. When it's `False`, it's not.
active = False


# PINDSVIND INCOMING

porcupine = pvporcupine.create(
    access_key=PICO_API_KEY, # use the api key
    keyword_paths=["Hey-Teddy.ppn"]  # Makes the keyword "Hey teddy" using the .ppnfile.
)

# set up pyaudio
pa = pyaudio.PyAudio()

# start listening
audio_stream = pa.open(
    rate=porcupine.sample_rate,
    channels=1,  
    format=pyaudio.paInt16,  
    input=True, 
    frames_per_buffer=porcupine.frame_length  
)

# Listens for the wake word
async def detect_wake_word():
    print("Listening for wake word...")
    global active

    # Loop that listens for wake word
    while True:
        # Read a chunk of audio data from the microphone.
        audio_frame = audio_stream.read(porcupine.frame_length)

        # Convert the raw audio data into numbers that Porcupine can understand.
        pcm = struct.unpack_from("h" * porcupine.frame_length, audio_frame)

        # Check if the wake word is in the audio data.
        keyword_index = porcupine.process(pcm)

        # If the wake word is detected.
        if keyword_index >= 0:
            print("Wake word detected!")  # Show the wake word is detected
            active = True  # Set `active` to `True` so the program starts responding.
            return # return to the main loop, now with "active" set to `True` which starts the other side of the program

# PINDSVIND OUTGOING

async def send_command():
    num_choices = random.choice([1, 2, 3])  # Randomly choose a number between one and three
    commands = random.sample(STRING, num_choices)  # Pick random commands
    command_str = " ".join(commands)  # Convert list to a space-separated string

    # Check if Arduino is connected
    if arduino.is_open:
        arduino.write((command_str + "\n").encode())  # Send command string
        await asyncio.sleep(1)  # Use await with asyncio.sleep()

        response = arduino.readline().decode().strip()  # Read response
        print("Arduino:", response)
        print("Python:", command_str)
    else:
        print("Arduino is not connected or communication error.")

# This is a class that helps us collect and manage the transcribed text.
class TranscriptCollector:
    def __init__(self):
        self.reset()  # Reset the script, in case there's something left from previous runs.

    def reset(self):
        # resets all the parts of the script.
        self.transcript_parts = []

    def add_part(self, part):
        # Add a new part to the script.
        self.transcript_parts.append(part)

    def get_full_transcript(self):
        # This combines all the parts into one full sentence.
        return ' '.join(self.transcript_parts).strip()

# Create an instance of TranscriptCollector to use later.
transcript_collector = TranscriptCollector()


# start gemini setup
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# This function generates a response from Gemini using a prompt.
def generate_message(prompt):
    response = gemini_client.models.generate_content(
        model="gemini-2.0-flash",  # This is the AI model
        contents=CRACK + prompt + NOGO  # These are special prompts for the AI.
    )
    return response.text  # Return the AI's response in a variable to read later

# This function generates audio from text using Deepgram.
def generate_audio(text):
    # use deepgram key
    deepgram = DeepgramClient(DEEPGRAM_API_KEY)

    # options for speech
    options = SpeakOptions(
        model="aura-luna-en",  # Set the voice
        encoding="linear16",
        sample_rate=16000
    )

    # Make deepgram generate audio and save it as an mp3
    response = deepgram.speak.v("2").save("response.wav", {"text": text}, options)

# This function plays the generated audio file.
def play_audio():
    """Plays the WAV file using PyAudio on Linux."""
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

        send_command()
        stream.stop_stream()
        stream.close()
        pa.terminate()
        wf.close()

    except Exception as e:
        # If something goes wrong, print an error message.
        print(f"Error playing file: {e}")
        return None

# This function deletes the audio file after it's been played.
def delete_audio():
    """Deletes the audio file after closing the media player."""
    try:
        # Get the length of the MP3 file
        audio = WAVE("response.wav")
        length = audio.info.length  # Add a little extra time to be safe.
        print(length)
        os.remove("response.wav")  # Delete the MP3 file.
        print(f"Deleted: response.wav")
    except Exception as e:
        # If something goes wrong, print an error message.
        print(f"Error deleting file: {e}")

# This function processes the transcribed text and generates a response.
async def process_transcript(full_sentence, dg_connection):
    global active

    # If the transcribed text is empty, do nothing.
    if not full_sentence:
        return

    # Print the transcribed text in the console.
    print(f"speaker: {full_sentence}")

    # If the user says "goodbye," shut down the program.
    if full_sentence.lower() == "goodbye.":
        print("Goodbye gonna kms")
        active = False  # Set `active` to `False` to stop the program.
        await dg_connection.finish()  # Stop the Deepgram connection.

    # Stop the Deepgram transcription.
    await dg_connection.finish()

    # Generate a response from Gemini using the transcribed text.
    response_text = generate_message(full_sentence)
    print(f"Gemini: {response_text}")

    # Turn the response text into audio and save it as an MP3 file.
    generate_audio(response_text)

    # Play the audio file.
    play_audio()

    # Delete the audio file after it's been played.
    delete_audio()

    # Clear the transcript so we're ready for the next sentence.
    transcript_collector.reset()

    # If the program is still active, restart the transcription.
    if active:
        await restart_transcription()

# This function restarts the Deepgram transcription after it has responded.
async def restart_transcription():
    print("Restarting transcription...")

    # Set up the Deepgram
    deepgram = DeepgramClient(DEEPGRAM_API_KEY)
    dg_connection = deepgram.listen.asynclive.v("1")

    # This function handles incoming transcribed text.
    async def on_message(self, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript  # Get the transcribed text.

        # If the sentence isn't final (meaning you haven't paused yet) add it to the transcript.
        if not result.speech_final:
            transcript_collector.add_part(sentence)
        else:
            # If the sentence is final, add it to the transcript and process it.
            transcript_collector.add_part(sentence)
            full_sentence = transcript_collector.get_full_transcript()

            # Process the full sentence.
            asyncio.create_task(process_transcript(full_sentence, dg_connection))

    # This function handles errors.
    async def on_error(self, error, **kwargs):
        print(f"\n\n{error}\n\n")

    # Set up event handlers for transcribed text and errors.
    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    # Set options for the live transcription.
    options = LiveOptions(
        model="nova-2",  # Use the Nova-2 model for transcription.
        punctuate=True,  # Add punctuation to the transcribed text.
        language="en-US",  # Use English as the language.
        encoding="linear16",  # Use a specific audio format.
        channels=1,  # idek, but it's important
        sample_rate=16000,  # set the sample rate in Hz.
        endpointing=True  # Detect when the user stops speaking.
    )

    # Start the Deepgram connection.
    await dg_connection.start(options)

    microphone = Microphone(dg_connection.send) # send audio to Deepgram
    microphone.start()

# This function gets the transcribed text from Deepgram.
async def get_transcript():
    global active

    try:
        # define deepgram and microphone
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        dg_connection = deepgram.listen.asynclive.v("1")
        microphone = Microphone(dg_connection.send)

        # This function handles incoming transcribed text.
        async def on_message(self, result, **kwargs):
            """Handles incoming transcripts and detects when a full sentence is received."""
            global active
            sentence = result.channel.alternatives[0].transcript  # Get the transcribed text.

            # If the sentence isn't final, add it to the transcript.
            if not result.speech_final:
                transcript_collector.add_part(sentence)
            else:
                # If the sentence is final, add it to the transcript and process it.
                transcript_collector.add_part(sentence)
                full_sentence = transcript_collector.get_full_transcript()

                # Process the full sentence.
                asyncio.create_task(process_transcript(full_sentence, dg_connection))

        # This function handles errors.
        async def on_error(self, error, **kwargs):
            print(f"\n\n{error}\n\n")

        # Set up event handlers for transcribed text and errors.
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)

        # Set options for the live transcription.
        options = LiveOptions(
            model="nova-2",  # Use the Nova-2 model for transcription.
            punctuate=True,  # Add punctuation to the transcribed text.
            language="en-US",  # Set language to English.
            encoding="linear16",  # Use a specific audio format.
            channels=1,  # Use one audio channel.
            sample_rate=16000,
            endpointing=True  # Detect when the user stops speaking.
        )

        # Start the Deepgram connection.
        await dg_connection.start(options)
        microphone.start()

        # Keep the program running while `active` is `True`.
        while active:
            await asyncio.sleep(1)

        # If `active` is `False`, stop the microphone and Deepgram connection.
        print("Trans stopped")
        microphone.finish()
        await dg_connection.finish()

    except Exception as e:
        # If something goes wrong, print an error message.
        print(f"Could not open socket: {e}")

if __name__ == "__main__":
    while True:
        asyncio.run(detect_wake_word())
        while active:
            asyncio.run(get_transcript())
