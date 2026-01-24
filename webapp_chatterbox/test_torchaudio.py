import torch
import torchaudio

print(f"Torchaudio version: {torchaudio.__version__}")

try:
    # Create a dummy waveform (1 second of silence, 44.1kHz)
    waveform = torch.zeros(1, 44100)
    sample_rate = 44100
    
    # Try applying tempo effect (0.8x)
    # Note: 'tempo' effect requires SoX. 'speed' changes pitch.
    effects = [['tempo', '0.8']]
    
    # apply_effects_tensor was added in newer versions, checking availability
    if hasattr(torchaudio.sox_effects, "apply_effects_tensor"):
        print("apply_effects_tensor is available.")
        out_wav, out_sr = torchaudio.sox_effects.apply_effects_tensor(waveform, sample_rate, effects)
        print("Success: Applied tempo effect.")
    else:
        print("apply_effects_tensor NOT available.")
        
except Exception as e:
    print(f"Error: {e}")
