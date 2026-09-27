# -*- coding: utf-8 -*-
"""Prod. 인트로 프리셋 — 리졸브 기본 타이틀 'Draw On Corners 1 Line' 에 tokens.json "intro" 값을 넣는다.

템플릿 자체는 블랙매직 것이라 이 리포에 싣지 않는다. 기본값에서 바꾸는 것은 셋뿐이다.
  Text1.StyledText      글자(기본 "Prod. NSBD", 인자로 바꿀 수 있음)
  Text1.Blue1           text_blue
  BoxColor.TopLeftBlue  box_blue
클립 길이와 끝 페이드도 tokens 값. 효과음은 docs/intro.md 참고.

현재 타임라인의 재생헤드 위치에 넣는다. 트랙은 리졸브가 정하는 대상 트랙이다.
    python scripts/intro_preset.py [글자]
"""
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import resolve_env

INTRO = json.load(open(os.path.join(HERE, "..", "tokens.json"), encoding="utf-8"))["intro"]


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else INTRO["text"]
    resolve = resolve_env.connect()
    proj = resolve.GetProjectManager().GetCurrentProject()
    tl = proj.GetCurrentTimeline() if proj else None
    if not tl:
        sys.exit("열린 타임라인이 없다")
    fps, _ = resolve_env.timeline_timing(tl)
    tc = tl.GetCurrentTimecode()
    at = resolve_env.tc_to_frame(tc, fps)
    length = INTRO["length_frames"]
    tl.SetMarkInOut(at, at + length - 1, "video")
    it = tl.InsertFusionTitleIntoTimeline(INTRO["template"])
    tl.ClearMarkInOut("all")
    if not it:
        sys.exit("타이틀을 넣지 못했다: %s" % INTRO["template"])
    comp = it.GetFusionCompByIndex(1)
    done = []
    for t in (comp.GetToolList(False) or {}).values():
        attrs = t.GetAttrs()
        if attrs.get("TOOLS_RegID") == "TextPlus":
            t.SetInput("StyledText", text)
            t.SetInput("Blue1", INTRO["text_blue"])
            done.append(attrs.get("TOOLS_Name"))
        elif attrs.get("TOOLS_Name") == "BoxColor":
            t.SetInput("TopLeftBlue", INTRO["box_blue"])
            done.append("BoxColor")
    it.SetFades({"FadeIn": 0, "FadeOut": INTRO["clip_fade_out_frames"]})
    it.SetName(text.replace("/", " "))
    print("inserted at %s (frame %d): %d frames, fade out %d, set: %s" % (
        tc, int(it.GetStart()), int(it.GetDuration()), INTRO["clip_fade_out_frames"], ", ".join(done)))
    if int(it.GetStart()) != at:
        print("warning: 넣은 자리 %d 가 재생헤드 %d 와 다르다" % (int(it.GetStart()), at))


if __name__ == "__main__":
    main()
