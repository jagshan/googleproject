import math
import struct
import wave
import numpy as np

SAMPLE_RATE = 44100
DURATION = 40.0  # seconds
BPM = 85.0
BEAT_SEC = 60.0 / BPM

# Note frequencies (Hz)
NOTES = {
    'C3': 130.81, 'E3': 164.81, 'G3': 196.00, 'B3': 246.94, 'D4': 293.66,
    'A2': 110.00, 'C4': 261.63, 'E4': 329.63, 'G4': 392.00,
    'D3': 146.83, 'F3': 174.61, 'A3': 220.00, 'C4': 261.63,
    'G2': 98.00,  'B2': 123.47, 'D3': 146.83, 'F3': 174.61,
}

# Warm 7th chord progression: Cmaj7 -> Am7 -> Dm7 -> G7
CHORDS = [
    [NOTES['C3'], NOTES['E3'], NOTES['G3'], NOTES['B3'], NOTES['D4']],  # Cmaj7(9)
    [NOTES['A2'], NOTES['C3'], NOTES['E3'], NOTES['G3'], NOTES['C4']],  # Am7
    [NOTES['D3'], NOTES['F3'], NOTES['A3'], NOTES['C4'], NOTES['E4']],  # Dm7(9)
    [NOTES['G2'], NOTES['B2'], NOTES['D3'], NOTES['F3'], NOTES['G4']],  # G7
]

def generate_lofi_track():
    num_samples = int(SAMPLE_RATE * DURATION)
    t = np.linspace(0, DURATION, num_samples, endpoint=False)
    audio = np.zeros(num_samples, dtype=np.float32)

    # 1. Generate Warm Rhodes/E-Piano Chords
    chord_duration_beats = 4.0  # 1 chord per bar (4 beats)
    chord_sec = chord_duration_beats * BEAT_SEC
    total_chords = int(np.ceil(DURATION / chord_sec))

    for idx in range(total_chords):
        chord_start_t = idx * chord_sec
        chord_idx = idx % len(CHORDS)
        chord_freqs = CHORDS[chord_idx]

        for freq in chord_freqs:
            # Generate synth sound with soft sine + harmonics and exponential decay
            start_i = int(chord_start_t * SAMPLE_RATE)
            length_i = int(chord_sec * SAMPLE_RATE)
            end_i = min(start_i + length_i, num_samples)
            if start_i >= num_samples:
                break

            dur = (end_i - start_i) / SAMPLE_RATE
            dt = np.linspace(0, dur, end_i - start_i, endpoint=False)

            # Warm harmonics with soft attack and decay
            env = np.exp(-1.5 * dt) * (1 - np.exp(-30 * dt))
            piano_wave = (
                0.6 * np.sin(2 * np.pi * freq * dt) +
                0.25 * np.sin(2 * np.pi * freq * 2 * dt) +
                0.15 * np.sin(2 * np.pi * freq * 3 * dt)
            ) * env

            audio[start_i:end_i] += piano_wave * 0.12

    # 2. Add Upbeat Lo-Fi Drum Beat (Kick, Snare, Hi-Hat)
    total_beats = int(np.ceil(DURATION / BEAT_SEC))
    for b in range(total_beats):
        b_time = b * BEAT_SEC
        b_idx = int(b_time * SAMPLE_RATE)

        # Kick on beat 0 and 2.5 (upbeat syncopated kick)
        if b % 4 == 0 or b % 4 == 2.5 or (b % 4 == 2 and (b // 4) % 2 == 1):
            kick_dur = 0.15
            k_len = int(kick_dur * SAMPLE_RATE)
            if b_idx + k_len < num_samples:
                k_dt = np.linspace(0, kick_dur, k_len, endpoint=False)
                # Pitch drop sweep for punchy sub kick
                kick_freq = 120 * np.exp(-25 * k_dt) + 45
                kick = np.sin(2 * np.pi * kick_freq * k_dt) * np.exp(-12 * k_dt) * 0.35
                audio[b_idx:b_idx + k_len] += kick

        # Snare / Rimshot on beat 1 and 3
        if b % 2 == 1:
            snare_dur = 0.12
            s_len = int(snare_dur * SAMPLE_RATE)
            if b_idx + s_len < num_samples:
                s_dt = np.linspace(0, snare_dur, s_len, endpoint=False)
                noise = np.random.uniform(-1, 1, s_len) * np.exp(-20 * s_dt)
                tone = np.sin(2 * np.pi * 180 * s_dt) * np.exp(-30 * s_dt)
                snare = (noise * 0.7 + tone * 0.3) * 0.22
                audio[b_idx:b_idx + s_len] += snare

        # Swing Hi-Hats every 8th note
        for sub in [0, 0.5]:
            hh_time = b_time + sub * BEAT_SEC
            hh_idx = int(hh_time * SAMPLE_RATE)
            hh_dur = 0.04
            h_len = int(hh_dur * SAMPLE_RATE)
            if hh_idx + h_len < num_samples:
                h_dt = np.linspace(0, hh_dur, h_len, endpoint=False)
                hihat = np.random.uniform(-1, 1, h_len) * np.exp(-60 * h_dt) * 0.08
                audio[hh_idx:hh_idx + h_len] += hihat

    # 3. Add Gentle Vinyl Crackle & Ambient Texture
    crackle = np.random.normal(0, 0.015, num_samples)
    # Sparse pop pops
    pops = (np.random.uniform(0, 1, num_samples) > 0.9995).astype(np.float32) * np.random.uniform(-0.15, 0.15, num_samples)
    audio += crackle + pops

    # 4. Low-pass filter for cozy warm lo-fi tone
    # Simple moving average filter to soften high frequencies
    kernel_size = 15
    kernel = np.ones(kernel_size) / kernel_size
    audio = np.convolve(audio, kernel, mode='same')

    # Normalize audio to prevent clipping
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = (audio / max_val) * 0.85

    # Export to WAV
    output_wav = "/config/.gemini/antigravity/brain/6a8e3fba-e894-4af4-ba9d-fafd30d38cca/lofi_track.wav"
    audio_int16 = (audio * 32767).astype(np.int16)

    with wave.open(output_wav, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())

    print(f"Lo-fi background music generated successfully: {output_wav}")
    return output_wav

if __name__ == "__main__":
    generate_lofi_track()
