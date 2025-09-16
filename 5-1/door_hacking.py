#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import zipfile
import argparse
import logging
from itertools import product
from multiprocessing import Process, Event, Queue, cpu_count

ALLOWED = 'abcdefghijklmnopqrstuvwxyz0123456789'
LENGTH = 6
REPORT_EVERY = 100_000
REPORT_INTERVAL = 1.0  # 초


def setup_logger(log_path='door_hacking.log'):
    """콘솔과 파일(UTF-8)로 동시에 로그를 남기는 로거를 설정한다."""
    logger = logging.getLogger('door_hacking')
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    # 파일(UTF-8)
    fh = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def _pick_smallest_member(zip_path):
    """검증 비용을 줄이기 위해 ZIP 안에서 가장 작은 파일 하나의 이름을 반환한다."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        infos = [i for i in zf.infolist() if not i.filename.endswith('/')]
        if not infos:
            return None
        return min(infos, key=lambda i: i.file_size).filename


def _worker(zip_path, target_name, prefixes, found_evt, result_q, progress_q, report_every):
    """워커 프로세스: 주어진 접두어 집합에 대해 남은 자릿수를 생성하며 비밀번호를 시도한다."""
    attempts = 0
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for first in prefixes:
                if found_evt.is_set():
                    return
                for tail in product(ALLOWED, repeat=LENGTH - 1):
                    if found_evt.is_set():
                        return

                    pwd_str = first + ''.join(tail)
                    attempts += 1

                    # 진행 누적을 배치로 전송해 IPC 오버헤드 감소
                    if attempts % report_every == 0:
                        progress_q.put(attempts)
                        attempts = 0

                    try:
                        # 가장 작은 파일만 읽어서 비밀번호 검증
                        zf.read(target_name, pwd=pwd_str.encode('utf-8'))
                        # 성공
                        if attempts:
                            progress_q.put(attempts)
                        result_q.put(('FOUND', pwd_str))
                        found_evt.set()
                        return
                    except RuntimeError:
                        # 비밀번호 불일치
                        continue
                    except NotImplementedError as e:
                        # 미지원 암호화/압축 방식
                        if attempts:
                            progress_q.put(attempts)
                        result_q.put(('UNSUPPORTED', repr(e)))
                        found_evt.set()
                        return
                    except Exception:
                        # 그 외 오류는 스킵하고 계속
                        continue
        # 루프 종료 시 잔여 시도 횟수 전송
        if attempts:
            progress_q.put(attempts)
    except Exception as e:
        if attempts:
            progress_q.put(attempts)
        result_q.put(('ERROR', repr(e)))
        found_evt.set()


def unlock_zip(zip_path='emergency_storage_key.zip', workers=None,
               report_every=REPORT_EVERY, report_interval=REPORT_INTERVAL,
               log_path='door_hacking.log'):
    """
    멀티프로세싱으로 [a-z0-9] 6자리 비밀번호를 무차별 대입으로 탐색한다.
    - 시작 시각, CPU 코어 수, 워커 수, 진행 상황(시도 수/경과/초당 시도), 성공/실패를 한글로 로그에 남긴다.
    - 성공 시 password.txt에 비밀번호를 저장하고, ZIP 전체를 해제한다.
    """
    logger = setup_logger(log_path)

    start_ts = time.time()
    start_human = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_ts))

    detected_cores = cpu_count() or 1
    workers = workers or detected_cores

    logger.info('[시작] %s', start_human)
    logger.info('[정보] 감지된 CPU 코어 수=%d, 사용할 워커 수=%d, 대상 ZIP="%s"',
                detected_cores, workers, zip_path)

    target_name = _pick_smallest_member(zip_path)
    if not target_name:
        logger.error('[오류] ZIP 안에 추출할 파일이 없습니다.')
        return None

    # 첫 글자 기준으로 접두어를 워커에 스트라이드로 배분
    prefixes = list(ALLOWED)
    buckets = [[] for _ in range(workers)]
    for idx, ch in enumerate(prefixes):
        buckets[idx % workers].append(ch)

    found_evt = Event()
    result_q = Queue()
    progress_q = Queue()
    procs = []

    for bucket in buckets:
        if not bucket:
            continue
        p = Process(
            target=_worker,
            args=(zip_path, target_name, bucket, found_evt, result_q, progress_q, report_every),
            daemon=True,
        )
        procs.append(p)
        p.start()

    total_attempts = 0
    last_report = start_ts
    found_pwd = None
    status = None
    status_payload = None

    # 메인 루프: 진행 집계 및 결과 수신
    while any(p.is_alive() for p in procs):
        # 진행 누적 비동기 수신
        drained = False
        while True:
            try:
                delta = progress_q.get_nowait()
                total_attempts += int(delta)
                drained = True
            except Exception:
                break

        now = time.time()
        if drained and now - last_report >= report_interval:
            elapsed = now - start_ts
            rate = total_attempts / elapsed if elapsed > 0 else 0.0
            logger.info('[진행] 시도수=%s, 경과=%.1f초, 속도=%.1f회/초',
                        f'{total_attempts:,}', elapsed, rate)
            last_report = now

        # 결과 확인
        try:
            kind, payload = result_q.get(timeout=0.1)
            status, status_payload = kind, payload
            if kind == 'FOUND':
                found_pwd = payload
                found_evt.set()
                break
            elif kind in ('UNSUPPORTED', 'ERROR'):
                found_evt.set()
                break
        except Exception:
            pass

    # 누락된 진행 누적 마지막 반영
    while True:
        try:
            delta = progress_q.get_nowait()
            total_attempts += int(delta)
        except Exception:
            break

    for p in procs:
        p.join(timeout=1.0)

    elapsed = time.time() - start_ts
    if found_pwd:
        rate = total_attempts / elapsed if elapsed > 0 else 0.0
        logger.info('[성공] 비밀번호를 찾았습니다: %s', found_pwd)
        logger.info('[통계] 총 시도수=%s, 총 소요=%.2f초, 평균 속도=%.1f회/초',
                    f'{total_attempts:,}', elapsed, rate)

        with open('password.txt', 'w', encoding='utf-8') as pwf:
            pwf.write(found_pwd + '\n')

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(pwd=found_pwd.encode('utf-8'))

        return found_pwd

    if status == 'UNSUPPORTED':
        logger.error('[실패] 미지원 암호화/압축 방식으로 추정됩니다(AES 등).')
    elif status == 'ERROR':
        logger.error('[실패] 워커 오류 발생: %s', status_payload)
    else:
        logger.error('[실패] 비밀번호를 찾지 못했습니다.')

    return None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description='멀티프로세싱으로 ZIP 비밀번호(6자리, [a-z0-9])를 무차별 대입으로 탐색합니다.'
    )
    parser.add_argument('zip_path', nargs='?', default='emergency_storage_key.zip',
                        help='대상 ZIP 파일 경로')
    parser.add_argument('--workers', type=int, default=0,
                        help='워커 프로세스 수(기본값: cpu_count)')
    parser.add_argument('--log', default='door_hacking.log',
                        help='로그 파일 경로(기본값: door_hacking.log)')
    parser.add_argument('--report-every', type=int, default=REPORT_EVERY,
                        help='워커가 진행 누적을 전송하는 배치 크기(기본값: 100000)')
    parser.add_argument('--report-interval', type=float, default=REPORT_INTERVAL,
                        help='진행 상황 출력 간격(초, 기본값: 1.0)')
    return parser.parse_args(argv)


if __name__ == '__main__':
    args = parse_args()
    workers = args.workers if args.workers > 0 else None
    unlock_zip(
        zip_path=args.zip_path,
        workers=workers,
        report_every=args.report_every,
        report_interval=args.report_interval,
        log_path=args.log,
    )
