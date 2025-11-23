import shutil, sys
print("python:", sys.executable)
from pydub import AudioSegment
print("converter:", AudioSegment.converter)
print("ffmpeg in PATH:", shutil.which("ffmpeg"))
seg = AudioSegment.from_file("lcwo-001-test.mp3")
print("durée (s):", seg.duration_seconds)
