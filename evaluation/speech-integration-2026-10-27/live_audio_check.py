"""Synthetic live audio probe; never reads or emits credentials."""
import asyncio
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import av
import httpx

ROOT = Path('C:/Users/User/OneDrive/Dokumente/MA Projekt/code')
sys.path.insert(0, str(ROOT))
from app.config import load_settings
from app.models import Language
from app.service_check import check_services
from app.speech import SpeechSynthesizer

PROOF = Path(__file__).parent
PHRASES = {
    'de': 'Ich brauche medizinische Hilfe.',
    'en': 'I need medical help.',
    'pl': 'Potrzebuję pomocy medycznej.',
    'ro': 'Am nevoie de ajutor medical.',
    'ru': 'Мне нужна медицинская помощь.',
}


def firefox_ogg(mp3):
    output = io.BytesIO()
    with av.open(io.BytesIO(mp3)) as source, av.open(output, mode='w', format='ogg') as dest:
        stream = dest.add_stream('libopus', rate=48000)
        stream.layout = 'mono'
        resampler = av.AudioResampler(format='s16', layout='mono', rate=48000)
        for frame in source.decode(audio=0):
            for converted in resampler.resample(frame):
                converted.pts = None
                for packet in stream.encode(converted):
                    dest.mux(packet)
        for converted in resampler.resample(None):
            converted.pts = None
            for packet in stream.encode(converted):
                dest.mux(packet)
        for packet in stream.encode(None):
            dest.mux(packet)
    return output.getvalue()


def audio_info(data):
    with av.open(io.BytesIO(data)) as container:
        frames = list(container.decode(audio=0))
        duration = sum(frame.samples / frame.sample_rate for frame in frames)
    assert duration > 0
    return {'bytes': len(data), 'seconds': round(duration, 3),
            'sha256': hashlib.sha256(data).hexdigest()}


def save_report(report):
    (PROOF/'live-audio-results.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


async def main():
    settings = load_settings()
    synth = SpeechSynthesizer(settings)
    report = {
        'date': '2026-10-27', 'content': 'synthetic only',
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python': sys.version.split()[0], 'edge_tts': importlib.metadata.version('edge-tts'),
        'stt_provider': settings.speech_transcription_provider,
        'tts_provider': settings.speech_synthesis_provider,
        'human_microphone_and_listening_review': 'pending', 'languages': {},
    }
    with httpx.Client(base_url='http://127.0.0.1:8002', timeout=60) as client:
        config = client.get('/api/speech/config')
        config.raise_for_status()
        report['speech_config'] = config.json()
        assert config.json()['server_transcription_available']
        assert config.json()['server_synthesis_available']
        save_report(report)
        for code, phrase in PHRASES.items():
            started = time.monotonic()
            entry = {'input_phrase': phrase}
            report['languages'][code] = entry
            try:
                source = await synth.synthesize(phrase, language=Language(code))
                ogg = firefox_ogg(source)
                (PROOF/f'{code}-synthetic-input.ogg').write_bytes(ogg)
                entry['input_ogg'] = audio_info(ogg)
                response = client.post('/api/speech/transcribe', params={'language': code},
                                       content=ogg, headers={'Content-Type': 'audio/ogg;codecs=opus'})
                entry['stt_http'] = response.status_code
                response.raise_for_status()
                entry['transcript'] = response.json()['text']
                assert entry['transcript'].strip()
                # A fixed preflight trigger creates a session-bound policy text
                # without invoking Interpreter, Selector or Formulator.
                query = client.post('/api/query', json={
                    'query': 'Ich kann gerade nicht atmen.', 'language': code,
                })
                query.raise_for_status()
                body = query.json()
                assert body['answer_type'] == 'acute_risk', body['answer_type']
                assert body['provider'] == 'template' and not body['cards']
                entry['tts_input'] = 'session-bound acute_risk policy; preflight, no LLM call'
                response = client.post('/api/speech/synthesize', json={
                    'text': body['answer'], 'language': code, 'session_id': body['session_id'],
                })
                entry['tts_http'] = response.status_code
                response.raise_for_status()
                assert response.headers['content-type'].startswith('audio/mpeg')
                entry['output_mp3'] = audio_info(response.content)
                (PROOF/f'{code}-policy-output.mp3').write_bytes(response.content)
                entry['result'] = 'technical_pass'
            except Exception as exc:
                entry['result'] = 'failed'
                entry['error_type'] = type(exc).__name__
                # No exception messages, HTTP headers or credential-bearing URLs.
                if isinstance(exc, httpx.HTTPStatusError):
                    entry['http_status'] = exc.response.status_code
                save_report(report)
                print(json.dumps({'language':code, **entry}, ensure_ascii=False), flush=True)
                raise
            entry['seconds'] = round(time.monotonic()-started, 2)
            save_report(report)
            print(json.dumps({'language':code, **entry}, ensure_ascii=False), flush=True)
    report['service_check'] = await asyncio.to_thread(check_services, settings, synthesize=True)
    save_report(report)


asyncio.run(main())
