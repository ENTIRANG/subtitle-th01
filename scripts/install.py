# -*- coding: utf-8 -*-
"""templates/*.setting 을 리졸브 사용자 타이틀 폴더의 th01 아래로 복사한다.
복사한 뒤에는 에디트 페이지 이펙트 → 타이틀 → Fusion 타이틀에 'th01 …' 으로 보인다(재시작 불필요).

    python scripts/install.py            # 설치
    python scripts/install.py --remove   # th01 폴더 지우기
"""
import os, sys, shutil

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "templates")


def titles_dir():
    if sys.platform == "win32":
        return os.path.expandvars(r"%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates\Edit\Titles")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Titles")
    return os.path.expanduser("~/.local/share/DaVinciResolve/Fusion/Templates/Edit/Titles")


def main():
    dst = os.path.join(titles_dir(), "th01")
    if "--remove" in sys.argv:
        shutil.rmtree(dst, ignore_errors=True)
        print("removed", dst)
        return
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(SRC)):
        if f.endswith(".setting"):
            shutil.copy(os.path.join(SRC, f), os.path.join(dst, f))
            n += 1
    print("%d templates -> %s" % (n, dst))


if __name__ == "__main__":
    main()
