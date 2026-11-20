"""Synthesizes the Act I enemy sounds that generated audio rendered as plain
hiss: the people's weapon swings and the Silver Spark's zap. The rest of
Assets/Sounds/Enemies came from ComfyUI's Stable Audio (seeds 7101-7136).

    python Tools/Sounds/enemy.py Assets/Sounds/Enemies

Each variant's random seed is fixed, so a run gives the same files."""
import sys
from pathlib import Path

import numpy as np

from swing import RATE, lowpass, swish, write


def zap(rng, seconds, hum_hz):
    """An arc: a buzzing hum with a wavering pitch, torn by crackles, in the
    band an electric snap lives in rather than across all of it."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    wobble = 1 + 0.08 * np.sin(2 * np.pi * rng.uniform(25, 40) * t) + 0.03 * rng.standard_normal(n).cumsum() / np.sqrt(n)
    phase = 2 * np.pi * np.cumsum(hum_hz * wobble) / RATE
    # A buzz rich in odd harmonics, as a mains hum or an arc has.
    hum = sum(np.sin(k * phase) / k for k in (1, 3, 5, 7, 9, 11))
    crackle = np.zeros(n)
    for at in rng.integers(0, int(n * 0.7), size=rng.integers(14, 22)):
        width = int(rng.uniform(0.0008, 0.003) * RATE)
        crackle[at:at + width] += rng.standard_normal(min(width, n - at)) * rng.uniform(0.6, 1.4)
    crackle = lowpass(crackle, 5000) - lowpass(crackle, 900)
    envelope = np.minimum(1, t / 0.006) * np.exp(-t / (seconds * 0.35))
    return (hum * 0.6 + crackle * 3.0) * envelope


def main():
    out = Path(sys.argv[1])
    for v in range(1, 5):
        rng = np.random.default_rng(7200 + v)
        j = lambda x: x * rng.uniform(0.9, 1.1)
        # A cudgel, sack or pole: slower and lower than her axe.
        write(out / f'human_attack_{v}.wav', swish(rng, j(0.32), 0.6, j(130), j(560), j(170), 1.4, 0.05))
        write(out / f'spark_attack_{v}.wav', zap(rng, j(0.35), j(110)))


if __name__ == '__main__':
    main()
