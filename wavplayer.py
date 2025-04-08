import wave
import pyaudio

def play_audio_file(filename):
    try:
        wf = wave.open(filename, "rb")
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
        print(f"Error playing {filename}: {e}")
