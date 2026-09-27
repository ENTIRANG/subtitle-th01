# -*- coding: utf-8 -*-
"""리졸브 스크립팅 연결과 타임코드 계산(scripts/ 의 다른 스크립트가 쓴다).

준비: 리졸브를 켜 두고, 환경설정 → System → General → External scripting using 을 Local 로 둔다.
스크립팅 모듈 위치는 블랙매직 기본 설치 경로를 쓰고, RESOLVE_SCRIPT_API · RESOLVE_SCRIPT_LIB 환경 변수가 있으면 그것을 쓴다."""
import os, re, sys

DEFAULTS = {
    "win32": (os.path.expandvars(r"%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"),
              r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"),
    "darwin": ("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting",
               "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"),
    "linux": ("/opt/resolve/Developer/Scripting", "/opt/resolve/libs/Fusion/fusionscript.so"),
}


def connect():
    api, lib = DEFAULTS.get(sys.platform, DEFAULTS["linux"])
    api = os.environ.setdefault("RESOLVE_SCRIPT_API", api)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", lib)
    mod = os.path.join(api, "Modules")
    if mod not in sys.path:
        sys.path.append(mod)
    try:
        import DaVinciResolveScript as dvr
    except ImportError:
        sys.exit("리졸브 스크립팅 모듈이 없다: %s — RESOLVE_SCRIPT_API 를 설치 경로의 Developer/Scripting 으로 둔다" % mod)
    resolve = dvr.scriptapp("Resolve")
    if not resolve:
        sys.exit("리졸브에 연결하지 못했다 — 리졸브를 켜고 환경설정 → System → General → External scripting using 을 Local 로 둔다")
    return resolve


def _drop(fps, drop):
    nominal = int(round(fps))
    return (2 if nominal == 30 else 4 if nominal == 60 else 0) if drop else 0, nominal


def tc_to_frame(tc, fps):
    """타임코드 → 프레임 번호. 29.97·59.94 드롭 프레임(';')도 센다."""
    d, nominal = _drop(fps, ";" in tc)
    h, m, s, f = [int(x) for x in re.split("[:;]", tc)]
    frames = ((h * 60 + m) * 60 + s) * nominal + f
    minutes = h * 60 + m
    return frames - d * (minutes - minutes // 10)


def frame_to_tc(frame, fps, drop=False):
    """프레임 번호 → 타임코드(tc_to_frame 의 역)."""
    d, nominal = _drop(fps, drop)
    if d:
        per10 = nominal * 600 - d * 9
        per1 = nominal * 60 - d
        tens, rem = divmod(frame, per10)
        frame += d * 9 * tens + (d * ((rem - d) // per1) if rem > d else 0)
    sep = ";" if d else ":"
    return "%02d:%02d:%02d%s%02d" % (frame // (3600 * nominal), (frame // (60 * nominal)) % 60, (frame // nominal) % 60, sep, frame % nominal)


def timeline_timing(tl):
    fps = float(tl.GetSetting("timelineFrameRate"))
    drop = str(tl.GetSetting("timelineDropFrameTimecode")) in ("1", "True", "true")
    return fps, drop
