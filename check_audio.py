
import pyaudio

p = pyaudio.PyAudio()
print("Available Audio Devices:")
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
found_input = False

for i in range(0, numdevices):
    if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
        print(f"Input Device id {i} - {p.get_device_info_by_host_api_device_index(0, i).get('name')}")
        found_input = True

if not found_input:
    print("No Input Devices Found.")
else:
    print("Input Device Available.")

p.terminate()
