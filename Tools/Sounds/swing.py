"""Synthesizes Hellfeather's weapon swing sounds, one set per kind of swing:
Blunt, heavy filtered-noise swishes and thumps for maces, hammers and axes, and
Sword, faster thinner swishes and ringing cuts. Each set has the wind-up, the
whoosh, the miss and the hit, the hits built on generated impacts.
Writes 16-bit mono 44.1 kHz WAVs peaking at -3 dB, into <out>/Blunt and <out>/Sword.

    python Tools/Sounds/swing.py Assets/Sounds/Swing Tools/Sounds/HitSources

HitSources holds the impacts made with ComfyUI's Stable Audio (seeds 6109-6112),
trimmed; the script filters their hiss off and lays a thump under them. Each
variant's random seed is fixed, so a run gives the same files."""
import sys
import wave
from pathlib import Path

import numpy as np

RATE = 44100


def bandpass_sweep(noise, centers, q):
    """A state-variable band-pass whose center follows `centers`, per sample."""
    low = band = 0.0
    out = np.empty_like(noise)
    damp = 1.0 / q
    for i, x in enumerate(noise):
        f = 2.0 * np.sin(np.pi * min(centers[i], RATE / 6) / RATE)
        high = x - low - damp * band
        band += f * high
        low += f * band
        out[i] = band
    return out


def lowpass(signal, cutoff):
    a = np.exp(-2 * np.pi * cutoff / RATE)
    out = np.empty_like(signal)
    y = 0.0
    for i, x in enumerate(signal):
        y = (1 - a) * x + a * y
        out[i] = y
    return out


def swish(rng, seconds, peak_at, start_hz, peak_hz, end_hz, q, decay):
    """Air moving past a blade: noise in a band that rises in pitch as the blade
    comes closest and falls away after, swelling to the pass and dying quickly."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    tp = peak_at * seconds
    rise = np.clip(t / tp, 0, 1) ** 2.5
    fall = np.exp(-np.maximum(t - tp, 0) / decay)
    envelope = rise * fall
    centers = np.where(t < tp,
                       start_hz * (peak_hz / start_hz) ** np.clip(t / tp, 0, 1),
                       peak_hz * (end_hz / peak_hz) ** np.clip((t - tp) / (seconds - tp), 0, 1))
    body = bandpass_sweep(rng.standard_normal(n), centers, q)
    # A little of the octave above, for air, still far below the hiss range.
    air = bandpass_sweep(rng.standard_normal(n), centers * 2.2, q * 1.5) * 0.35
    signal = (body + air) * envelope
    fade = min(n, int(0.01 * RATE))
    signal[-fade:] *= np.linspace(1, 0, fade)
    shaped = lowpass(signal, 3000)
    # Without the rumble under the band, which only muddies a swish.
    return shaped - lowpass(shaped, 90)


def thump(rng, seconds, top_hz, bottom_hz, decay):
    """A blow's weight: a falling low tone and a short dull crunch."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    pitch = bottom_hz + (top_hz - bottom_hz) * np.exp(-t / 0.03)
    tone = np.sin(2 * np.pi * np.cumsum(pitch) / RATE) * np.exp(-t / decay)
    crunch = lowpass(rng.standard_normal(n), 1200) * np.exp(-t / 0.018) * 2.0
    return tone + crunch


def ring(rng, seconds, base_hz, decay):
    """Struck steel: inharmonic partials, as a bar's are, dying away together."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    tone = np.zeros(n)
    for ratio, level in ((1.0, 1.0), (2.76, 0.6), (5.40, 0.35), (8.93, 0.2)):
        f = base_hz * ratio * rng.uniform(0.99, 1.01)
        if f < RATE / 2.5:
            tone += level * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t * ratio ** 0.5 / decay)
    return tone * np.minimum(1, t / 0.002)


def slice_burst(rng, seconds):
    """The edge going in: a short bright tear of noise."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    noise = rng.standard_normal(n)
    band = lowpass(noise, 6000) - lowpass(noise, 1800)
    return band * np.exp(-t / 0.025)


def mix(*parts):
    """Each part, scaled to its own peak times its level, summed from the start."""
    n = max(len(sound) for sound, _ in parts)
    out = np.zeros(n)
    for sound, level in parts:
        out[:len(sound)] += sound / max(1e-9, np.abs(sound).max()) * level
    return out


def read(path):
    with wave.open(str(path)) as f:
        data = np.frombuffer(f.readframes(f.getnframes()), dtype='<i2').astype(float) / 32768
    return data


def write(path, signal):
    signal = signal / max(1e-9, np.abs(signal).max()) * 10 ** (-3 / 20)
    pcm = (signal * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(pcm.tobytes())
    print(path.name, f'{len(signal) / RATE:.3f}s')


def blunt(out, hits):
    for v in range(1, 5):
        rng = np.random.default_rng(7000 + v)
        j = lambda x: x * rng.uniform(0.9, 1.1)
        # The wind-up: the weapon drawn back, a slow soft low swish.
        write(out / f'start_{v}.wav', swish(rng, j(0.22), 0.6, j(120), j(320), j(160), 1.2, 0.05))
        # The downswing: heavy and fast, peaking late as the head passes.
        write(out / f'whoosh_{v}.wav', swish(rng, j(0.26), 0.62, j(170), j(750), j(220), 1.6, 0.045))
        # A miss: the follow-through dying away under her.
        write(out / f'end_{v}.wav', swish(rng, j(0.3), 0.12, j(500), j(420), j(130), 1.3, 0.09))
        # A hit: the generated impact without its hiss, over a low thump.
        impact = lowpass(hits[v - 1], 3500)
        weight = thump(rng, 0.35, j(140), j(55), j(0.09))
        write(out / f'hit_{v}.wav', mix((impact, 1.0), (weight, 0.8)))


def sword(out, hits):
    for v in range(1, 5):
        rng = np.random.default_rng(7300 + v)
        j = lambda x: x * rng.uniform(0.9, 1.1)
        # The wind-up: a light blade turned back, quick and airy.
        write(out / f'start_{v}.wav', swish(rng, j(0.16), 0.6, j(260), j(700), j(320), 1.4, 0.035))
        # The cut: a thin fast whistle, higher than a mace's, peaking late.
        write(out / f'whoosh_{v}.wav', swish(rng, j(0.2), 0.65, j(380), j(1500), j(450), 2.2, 0.03))
        # A miss: the blade running on through the air and away.
        write(out / f'end_{v}.wav', swish(rng, j(0.24), 0.1, j(1000), j(800), j(300), 1.8, 0.06))
        # A hit: a crisper impact, the edge tearing in and a short ring of
        # steel, over a lighter thump than a mace's.
        impact = lowpass(hits[v - 1], 6000)
        weight = thump(rng, 0.25, j(200), j(90), j(0.05))
        edge = slice_burst(rng, 0.12)
        steel = ring(rng, 0.4, j(1150), 0.09)
        write(out / f'hit_{v}.wav', mix((impact, 0.9), (edge, 0.6), (steel, 0.28), (weight, 0.45)))


def main():
    out = Path(sys.argv[1])
    sources = Path(sys.argv[2])  # The trimmed generated hits, hit_1..4.wav.
    hits = [read(sources / f'hit_{v}.wav') for v in range(1, 5)]
    for name, build in (('Blunt', blunt), ('Sword', sword)):
        (out / name).mkdir(parents=True, exist_ok=True)
        build(out / name, hits)


if __name__ == '__main__':
    main()
