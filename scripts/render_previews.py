# -*- coding: utf-8 -*-
"""설치된 th01 템플릿을 임시 타임라인 _th01_preview 에 하나씩 깔고, 정해 둔 프레임을 PNG 로 뽑는다(docs/img).

렌더 대기열은 쓰지 않는다. 템플릿마다 V1 한 트랙에 혼자 놓이므로 Project.ExportCurrentFrameAsStill 로
그 클립의 합성 결과가 그대로 나온다. 미리보기용 배경(벽 그라데이션)은 각 클립의 퓨전 안에서
템플릿 출력 아래에 깔고, 템플릿 자체는 건드리지 않는다. 끝나면 임시 타임라인을 지운다.

기준 템플릿(cm)은 tokens.json pipeline 설정(색 관리 v2, Rec.709 Scene, SDR 100)의 프로젝트에서,
--variant yrgb 는 색 관리 없는(DaVinci YRGB) 프로젝트에서 돌린다. 준비는 resolve_env.py 참고.

    python scripts/install.py
    python scripts/render_previews.py [출력 폴더] [--variant cm|yrgb] [--only 이름,이름] [--size 3840x2160]
"""
import os, sys, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "build"))
import resolve_env
import elements                                   # 미리보기 배경 색을 색 설정에 맞춰 쓰려고

TOK = elements.T
QR = os.path.join(ROOT, "docs", "qr-sample.png")

# (파일 이름, 템플릿, 클립 길이, 뽑을 프레임, 배경[, 입력값])  배경: "wall" 벽 그라데이션 / "dark" 먹색 / None 템플릿 그대로
# 입력값은 {인스펙터 이름 또는 Input 번호: 값}
PREVIEWS = [
    ("subtitle-bar", "th01 자막바", 150, [30], "wall"),
    ("caption", "th01 자막", 90, [30], "wall"),
    ("question", "th01 질문", 150, [30], "wall"),
    ("two-choice", "th01 이지선다", 150, [30], "wall"),
    ("info-card", "th01 안내 카드", 120, [60], None),
    ("link", "th01 링크", 120, [30], "wall"),
    ("qr-card", "th01 QR 카드", 226, [100], None),
    ("form-demo", "th01 폼 데모", 227, [80, 170], None),
    ("opening", "th01 오프닝 타이틀", 151, [75], "dark"),
    ("section", "th01 섹션 타이틀", 184, [90], "dark"),
    ("credits", "th01 크레딧", 114, [57], None),       # 템플릿에 불투명 검은 판이 있다
    ("watermark", "th01 워터마크", 150, [75], "dark"),
]


def template_name(tpl, variant):
    return tpl + TOK["pipeline"]["variants"][variant]["suffix"]


def add_background(item, dur, kind):
    """클립 퓨전에 배경 + Merge 를 넣어 MediaOut 앞에 끼운다. 새 툴은 렌더 범위가 0~149 라 GlobalOut 을 먼저 준다."""
    comp = item.GetFusionCompByIndex(1)
    if not comp or not kind:
        return bool(comp)
    mo = next((t for t in (comp.GetToolList(False) or {}).values() if t.GetAttrs().get("TOOLS_RegID") == "MediaOut"), None)
    if not mo:
        raise RuntimeError("MediaOut 을 못 찾았다: %s" % sorted(t.GetAttrs().get("TOOLS_Name") for t in (comp.GetToolList(False) or {}).values()))
    src = mo.FindMainInput(1).GetConnectedOutput()
    comp.Lock()
    bg = comp.AddTool("Background", -32768, -32768)
    mg = comp.AddTool("Merge", -32768, -32768)
    for t in (bg, mg):
        t.SetInput("GlobalOut", dur - 1)
        t.SetInput("GlobalIn", 0)
    bg.SetInput("UseFrameFormatSettings", 1)         # 타임라인 해상도
    bg.SetInput("Type", "Vertical")                  # 숫자를 주면 조용히 무시되고 빈 화면이 된다
    c = elements.C                                   # set_pipeline 한 색 설정의 값
    top, bottom = (c["wall-top"], c["wall-bottom"]) if kind == "wall" else (c["ink"], c["ink"])
    for corner, rgb in (("TopLeft", top), ("TopRight", top), ("BottomLeft", bottom), ("BottomRight", bottom)):
        for ch, v in zip(("Red", "Green", "Blue"), rgb):
            bg.SetInput(corner + ch, v)
        bg.SetInput(corner + "Alpha", 1)
    mg.ConnectInput("Background", bg)
    mg.ConnectInput("Foreground", src)
    mo.ConnectInput("Input", mg)
    comp.Unlock()
    return True


def set_inputs(item, values):
    """템플릿(매크로)의 공개 입력을 이름(인스펙터에 보이는 것) 또는 ID(Input1…)로 바꾼다. 못 찾은 이름을 돌려준다."""
    comp = item.GetFusionCompByIndex(1)
    left = dict(values)
    for t in (comp.GetToolList(False) or {}).values():
        if t.GetAttrs().get("TOOLS_RegID") != "MacroOperator":
            continue
        for inp in (t.GetInputList() or {}).values():
            a = inp.GetAttrs()
            for key in (a.get("INPS_Name"), a.get("INPS_ID")):
                if key in left:
                    t.SetInput(a["INPS_ID"], left.pop(key))
                    break
    return sorted(left)


def set_qr(item, path):
    comp = item.GetFusionCompByIndex(1)
    for t in (comp.GetToolList(False) or {}).values():
        if t.GetAttrs().get("TOOLS_Name") == "th_qr":
            t.SetInput("Clip", path)
            return True
    return False


def run(resolve, proj, out, jobs=PREVIEWS, settle=1.5, variant="cm", size=None):
    os.makedirs(out, exist_ok=True)
    elements.set_pipeline(variant)
    mp = proj.GetMediaPool()
    main = proj.GetCurrentTimeline()
    for i in range(proj.GetTimelineCount() or 0, 0, -1):
        t = proj.GetTimelineByIndex(i)
        if t.GetName() == "_th01_preview":
            mp.DeleteTimelines([t])
    tl = mp.CreateEmptyTimeline("_th01_preview")
    proj.SetCurrentTimeline(tl)
    if size:
        tl.SetSetting("useCustomSettings", "1")
        tl.SetSetting("timelineResolutionWidth", str(size[0]))
        tl.SetSetting("timelineResolutionHeight", str(size[1]))
    fps, drop = resolve_env.timeline_timing(tl)
    st = tl.GetStartFrame()
    rep, placed, at = [], [], 0
    try:
        for job in jobs:
            name, tpl, dur, frames, bg = job[:5]
            values = job[5] if len(job) > 5 else None
            tpl = template_name(tpl, variant)
            tl.SetCurrentTimecode(resolve_env.frame_to_tc(st + at, fps, drop))
            tl.SetMarkInOut(st + at, st + at + dur - 1, "video")
            it = tl.InsertFusionTitleIntoTimeline(tpl)
            tl.ClearMarkInOut("all")
            row = {"name": name, "template": tpl, "inserted": bool(it)}
            if it:
                row["pos"] = [int(it.GetStart()) - st, int(it.GetDuration())]
                row["background"] = add_background(it, dur, bg)
                if values:
                    row["unset"] = set_inputs(it, values)
                if name == "qr-card" and os.path.isfile(QR):
                    row["qr"] = set_qr(it, os.path.abspath(QR))
                placed.append((name, at, frames))
            rep.append(row)
            at += dur
        page = resolve.GetCurrentPage()
        resolve.OpenPage("color")                       # 스틸 내보내기는 컬러 페이지에서만 된다
        for name, at0, frames in placed:
            for f in frames:
                tl.SetCurrentTimecode(resolve_env.frame_to_tc(st + at0 + f, fps, drop))
                time.sleep(settle)
                p = os.path.abspath(os.path.join(out, "%s.png" % name if len(frames) == 1 else "%s-%03d.png" % (name, f)))
                if os.path.exists(p):
                    os.remove(p)
                ok = proj.ExportCurrentFrameAsStill(p)
                if not ok or not os.path.isfile(p):       # 새 템플릿 첫 프레임은 늦게 나올 때가 있다
                    time.sleep(settle * 2)
                    ok = proj.ExportCurrentFrameAsStill(p)
                rep.append({"file": os.path.basename(p), "ok": bool(ok) and os.path.isfile(p)})
        if page:
            resolve.OpenPage(page)
    finally:
        if main:
            proj.SetCurrentTimeline(main)
        mp.DeleteTimelines([tl])
    return rep


def parse(argv):
    opt = {"out": os.path.join(ROOT, "docs", "img"), "variant": "cm", "only": None, "size": None}
    it = iter(argv)
    for a in it:
        if a == "--variant":
            opt["variant"] = next(it)
        elif a == "--only":
            opt["only"] = next(it).split(",")
        elif a == "--size":
            opt["size"] = tuple(int(x) for x in next(it).lower().split("x"))
        else:
            opt["out"] = a
    return opt


if __name__ == "__main__":
    o = parse(sys.argv[1:])
    jobs = [j for j in PREVIEWS if not o["only"] or j[0] in o["only"]]
    resolve = resolve_env.connect()
    proj = resolve.GetProjectManager().GetCurrentProject()
    print(json.dumps(run(resolve, proj, o["out"], jobs, variant=o["variant"], size=o["size"]), ensure_ascii=False, indent=1))
