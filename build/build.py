# -*- coding: utf-8 -*-
"""tokens.json → templates/*.setting (Fusion 타이틀 매크로).

색 설정마다 한 벌씩 만든다(tokens.json pipeline.variants): 기준(cm)은 'th01 자막바', 색 관리 없는 프로젝트용(yrgb)은
'th01 자막바 (색 관리 없음)'. 만든 뒤 순환 검사를 통과하지 못하면 설치하지 않는다.

    python build/build.py             # templates/ 에 쓰기
    python build/build.py --install   # 리졸브 사용자 타이틀 폴더(th01)에도 복사
"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elements
import form
import flea
import check_cycles

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "templates")
ELEMENTS = elements.ELEMENTS + form.ELEMENTS + flea.ELEMENTS
VARIANTS = elements.T["pipeline"]["variants"]


def resolve_titles_dir():
    if sys.platform == "win32":
        return os.path.expandvars(r"%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates\Edit\Titles")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Titles")
    return os.path.expanduser("~/.local/share/DaVinciResolve/Fusion/Templates/Edit/Titles")


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):                        # 이름이 바뀐 옛 템플릿이 남지 않게
        if f.endswith(".setting"):
            os.remove(os.path.join(OUT, f))
    names = []
    for variant, spec in VARIANTS.items():
        elements.set_pipeline(variant)
        for name, fn, dur in ELEMENTS:
            m = fn()
            text = m.to_setting(variant) if isinstance(m, flea.WrappedMacro) else m.to_setting()
            full = name + spec["suffix"]
            p = os.path.join(OUT, full + ".setting")
            open(p, "w", encoding="utf-8", newline="\n").write(text)
            names.append((full, dur, os.path.getsize(p)))
    elements.set_pipeline("cm")
    for n, d, s in names:
        print("%-34s %7d bytes  (권장 길이 %d 프레임)" % (n, s, d))
    bad = []
    for n, d, s in names:
        path = os.path.join(OUT, n + ".setting")
        se = check_cycles.syntax_errors(path)
        if se:
            bad.append(n)
            print("SYNTAX", n, "; ".join(se[:3]))
        cs = check_cycles.cycles(check_cycles.graph(check_cycles.parse(path)))
        if cs:
            bad.append(n)
            print("CYCLE", n, " -> ".join("%s(%s)" % (k[1], k[0]) for k in cs[0]))
    if bad:
        sys.exit("문법 오류나 순환 참조가 있어 설치하지 않는다: %s" % ", ".join(bad))
    if "--install" in sys.argv:
        dst = os.path.join(resolve_titles_dir(), "th01")
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(dst):
            if f.endswith(".setting") and not os.path.exists(os.path.join(OUT, f)):
                os.remove(os.path.join(dst, f))
        for f in os.listdir(OUT):
            if f.endswith(".setting"):
                shutil.copy(os.path.join(OUT, f), os.path.join(dst, f))
        print("installed ->", dst)


if __name__ == "__main__":
    main()
