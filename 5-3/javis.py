#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import csv
import json
import wave
import zipfile
import urllib.request
from pathlib import Path
from datetime import datetime

# 외부 라이브러리 (허용 범위: 마이크 녹음, STT)
import pyaudio  # pip install pyaudio
from vosk import Model, KaldiRecognizer  # pip install vosk

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
RECORDS_DIR = BASE_DIR / 'records'
MODELS_DIR = BASE_DIR / 'models'
# 한국어 소형 모델(공식 목록에 등재된 파일 URL)
VOSK_KO_SMALL_URL = 'https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip'
VOSK_KO_SMALL_DIRNAME = 'vosk-model-small-ko-0.22'

# 오디오 설정 (Vosk STT 친화적 파라미터)
RATE = 16000       # 16 kHz
CHANNELS = 1       # 모노
SAMPLE_FORMAT = pyaudio.paInt16
CHUNK = 1024       # 프레임 크기


def ensure_records_dir() -> None:
    RECORDS_DIR.mkdir(parents=True, exist_ok=True)


def timestamp_filename() -> str:
    # ‘년월일-시간분초’ -> 20250923-154755
    return datetime.now().strftime('%Y%m%d-%H%M%S')


def record_audio() -> Path:
    """
    Ctrl+C 로 녹음을 종료한다.
    """
    ensure_records_dir()
    filename = f'{timestamp_filename()}.wav'
    filepath = RECORDS_DIR / filename

    pa = pyaudio.PyAudio()
    stream = None
    frames = []

    try:
        print('[녹음 시작] Ctrl+C 로 종료합니다.')
        stream = pa.open(format=SAMPLE_FORMAT,
                         channels=CHANNELS,
                         rate=RATE,
                         input=True,
                         frames_per_buffer=CHUNK)
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
    except KeyboardInterrupt:
        print('\n[녹음 종료]')
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        pa.terminate()

    # WAV 파일 저장 (표준 라이브러리 wave)
    with wave.open(str(filepath), 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pa.get_sample_size(SAMPLE_FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    print(f'[저장 완료] {filepath}')
    return filepath


def list_recordings() -> list[Path]:
    ensure_records_dir()
    wavs = sorted(RECORDS_DIR.glob('*.wav'))
    return wavs


def download_and_extract_model(url: str, dest_dir: Path, expected_dirname: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / 'model.zip'
    print('[모델 다운로드] 잠시만 기다려 주세요...')
    urllib.request.urlretrieve(url, str(zip_path))
    print('[압축 해제]')

    model_dir = dest_dir / expected_dirname
    with zipfile.ZipFile(str(zip_path), 'r') as zf:
        zf.extractall(str(dest_dir))
    zip_path.unlink(missing_ok=True)

    if not model_dir.exists():
        # 압축 내부 디렉터리명이 다를 경우 첫 디렉터리를 모델 경로로 간주
        subdirs = [p for p in dest_dir.iterdir() if p.is_dir()]
        if subdirs:
            return subdirs[0]
    return model_dir


def ensure_korean_model() -> Path:
    model_path = MODELS_DIR / VOSK_KO_SMALL_DIRNAME
    if model_path.exists():
        return model_path
    return download_and_extract_model(VOSK_KO_SMALL_URL, MODELS_DIR, VOSK_KO_SMALL_DIRNAME)


def transcribe_wav_to_csv(wav_path: Path, model_path: Path) -> Path:
    """
    Vosk로 STT를 수행하고 세그먼트 시작 시간을 함께 CSV로 저장한다.
    CSV 헤더: [음성 파일내에서의 시간, 인식된 텍스트]
    """
    csv_path = wav_path.with_suffix('.CSV')

    with wave.open(str(wav_path), 'rb') as wf:
        if wf.getnchannels() != 1 or wf.getframerate() != RATE:
            print(f'[경고] {wav_path.name}: 16kHz 모노 PCM이 아닙니다. 녹음 설정을 확인하세요.')
            return csv_path

        model = Model(str(model_path))
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)

        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part = json.loads(rec.Result())
                if part.get('text'):
                    results.append(part)
        final_part = json.loads(rec.FinalResult())
        if final_part.get('text'):
            results.append(final_part)

    # CSV 저장
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['음성 파일내에서의 시간', '인식된 텍스트'])
        for seg in results:
            words = seg.get('result', [])
            if not words:
                continue
            start_time = words[0].get('start', 0.0)
            text = ' '.join(w.get('word', '') for w in words).strip()
            writer.writerow([f'{start_time:.2f}', text])

    print(f'[STT 완료] {wav_path.name} → {csv_path.name}')
    return csv_path


def transcribe_all() -> None:
    wavs = list_recordings()
    if not wavs:
        print('[안내] records 폴더에 WAV 파일이 없습니다. 먼저 녹음을 수행하세요.')
        return
    model_path = ensure_korean_model()
    for wav in wavs:
        transcribe_wav_to_csv(wav, model_path)


def main() -> None:
    ensure_records_dir()
    while True:
        print('\n=== javis.py ===')
        print('1) 녹음 시작')
        print('2) 녹음 목록 보기')
        print('3) STT 실행(전체 WAV → CSV)')
        print('4) 종료')
        choice = input('선택: ').strip()
        if choice == '1':
            record_audio()
        elif choice == '2':
            files = list_recordings()
            if not files:
                print('[안내] 녹음 파일이 없습니다.')
            else:
                for p in files:
                    print(f'- {p.name}')
        elif choice == '3':
            transcribe_all()
        elif choice == '4':
            print('종료합니다.')
            break
        else:
            print('올바른 번호를 입력하세요.')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'[오류] {e}')
        sys.exit(1)
