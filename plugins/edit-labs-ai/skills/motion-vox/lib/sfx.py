"""Build a separate, explicitly timed SFX layer. Does not select or submit media."""
import json
import math
import subprocess
from pathlib import Path

RATE = 48000


def build_audio(events, first_input, root, duration):
    """Return (extra ffmpeg inputs, filters, audio map, codec args).

    Empty events bypass filtering/reencoding. Each selected event is trimmed in source
    time and delayed so its anchor coincides with timeline_at, at sample precision.
    """
    if not isinstance(events, list):
        raise ValueError('SFX_EVENTS must be a list; use [] explicitly for no SFX')
    if not events:
        return [], [], '0:a:0', ['-c:a', 'copy']
    inputs, filters, labels = [], [], ['[0:a:0]']
    durations = {}
    for i, e in enumerate(events):
        required = ('source_in', 'source_out', 'anchor_at', 'timeline_at',
                    'gain_db', 'fade_in', 'fade_out')
        values = {}
        for key in required:
            v = e[key]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f'SFX {i}: {key} must be a finite number')
            values[key] = float(v)
        if not e.get('reason', '').strip():
            raise ValueError(f'SFX {i}: reason is required')
        path = Path(e['source'])
        if not path.is_absolute():
            path = Path(root) / path
        path = path.resolve(strict=True)
        if path not in durations:
            probe = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_type:format=duration', '-of', 'json', str(path)]))
            if not probe.get('streams'):
                raise ValueError(f'SFX {i}: no audio stream: {path.name}')
            durations[path] = float(probe['format']['duration'])
        a, b, anchor = (values[k] for k in ('source_in', 'source_out', 'anchor_at'))
        fi, fo, gain = (values[k] for k in ('fade_in', 'fade_out', 'gain_db'))
        length = b - a
        start = values['timeline_at'] - (anchor - a)
        if not (0 <= a <= anchor < b <= durations[path] + 1 / RATE):
            raise ValueError(f'SFX {i}: source bounds/anchor outside audio')
        if start < 0 or start + length > duration + 1 / RATE:
            raise ValueError(f'SFX {i}: sound extends beyond the video; revise the cue')
        if gain > 0 or fi < 0 or fo < 0 or fi + fo > length:
            raise ValueError(f'SFX {i}: invalid attenuation or fades')
        inputs += ['-i', str(path)]
        delay = round(start * RATE)
        chain = (f'[{first_input+i}:a:0]atrim=start={a:.9f}:end={b:.9f},'
                 f'asetpts=PTS-STARTPTS,aresample={RATE},'
                 'aformat=sample_fmts=fltp:channel_layouts=stereo')
        if fi:
            chain += f',afade=t=in:st=0:d={fi:.9f}'
        if fo:
            chain += f',afade=t=out:st={length-fo:.9f}:d={fo:.9f}'
        chain += f',volume={gain:.6f}dB,adelay={delay}S:all=1[sfx{i}]'
        filters.append(chain)
        labels.append(f'[sfx{i}]')
    filters.append(''.join(labels) + f'amix=inputs={len(labels)}:duration=first:'
                   'dropout_transition=0:normalize=0[aout]')
    return inputs, filters, '[aout]', ['-c:a', 'aac', '-b:a', '256k']
