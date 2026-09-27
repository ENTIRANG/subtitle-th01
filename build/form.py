# -*- coding: utf-8 -*-
"""th01 폼 데모 — 휴대폰 속 신청 폼이 채워지는 장면 + 오른쪽 안내 카드.

색·글자 크기·애니메이션 프레임·휴대폰과 카드 자리는 tokens.json "form". 폼 색은 폼 페이지의 화면색이라
fusion_color 가 색 설정에 맞춰 바꾼다. 휴대폰 화면 안의 세부 배치(폼 카드 높이, 줄 간격)는 아래 상수로 둔다 —
폼 페이지 한 화면을 옮긴 것이라 다른 요소와 나눠 쓰지 않는다."""
import fu
from elements import (T, macro, color_master, fade_controls, Stack, solid_ref, text_ref, pills, card_publish, finish, fit_text,
                      fusion_color, X, Y, C, CARD, DISPLAY, LAY)

F = T["form"]
FS = F["size"]
FR = F["frames"]

# 휴대폰 화면 안 배치(px)
TOP_PAD = 56              # 화면 윗선 → 제목 카드
TITLE_CARD_H = 222.0      # 제목 카드 높이
CARD_GAP = 12             # 폼 카드 사이
CARD_SIDE = 12            # 화면 양옆 → 폼 카드
TEXT_SIDE = 20            # 폼 카드 왼끝 → 글자
DONE_CARD_H = 210.0       # 완료 화면 카드 높이


def form_demo():
    FORM = {k: fusion_color(h) for k, h in F["colors"].items()}
    m = macro("th01_FormDemo")
    ref = color_master(m, "th_color", C["speaker-3"])
    fexp = fade_controls(m)
    st = Stack(m, m.add(fu.canvas("th_canvas")).name)
    wall_m = st.over(m.add(fu.gradient_v("th_wall", C["wall-top"], C["wall-bottom"])).name, blend=1)
    ct = Stack(m, m.add(fu.canvas("th_canvas_c")).name)
    ct.i = 100
    cnt = [0]

    def key(k):
        cnt[0] += 1
        return "%s%d" % (k, cnt[0])

    def anim(tool_merge, k, keys):
        sp = m.add(fu.spline("th_S" + k, keys))
        tool_merge.inputs["Blend"] = fu.inp(src=sp.name, out="Value")

    def pbox(k, cxp, cyp, wp, hp, rp, rgb, blend=None):
        k = key(k)
        r = m.add(fu.rect("th_R" + k, X(cxp), 1 - Y(cyp), X(wp), Y(hp), (rp / (min(wp, hp) / 2.0)) if rp else 0.0))
        s = m.add(fu.solid("th_" + k, rgb, r.name))
        mg = ct.over(s.name)
        if isinstance(blend, dict):
            anim(mg, k, blend)
        return mg

    def ptext(k, s, style, size, xp, yp, rgb, align=-1, blend=None, write=None, font="Pretendard"):
        k = key(k)
        t = m.add(fu.text("th_t" + k, s, font, style, size, X(xp), 1 - Y(yp), rgb, align=align))
        if write:
            sp = m.add(fu.spline("th_W" + k, write))
            t.inputs["End"] = fu.inp(src=sp.name, out="Value")
        again(t, blend)
        return t

    def again(t, blend=None):
        """이미 만든 글자를 한 번 더 얹는다(같은 글자가 두 화면에 나올 때 — 고치면 둘 다 바뀐다)."""
        mg = ct.over(t.name)
        if isinstance(blend, dict):
            anim(mg, key("again"), blend)

    pubs = []
    P = F["phone"]
    PX, PY = map(float, P["center_px"])
    PW, PH = map(float, P["size_px"])
    ins = P["screen_inset_px"]
    pbox("shadow", PX + P["shadow_offset_px"][0], PY + P["shadow_offset_px"][1], PW, PH, float(P["shadow_radius_px"]), FORM["shadow"])
    pbox("phone", PX, PY, PW, PH, float(P["radius_px"]), FORM["phone"])
    SX0, SY0, SW, SH = PX - PW / 2 + ins, PY - PH / 2 + ins, PW - 2 * ins, PH - 2 * ins
    pbox("screen", PX, PY, SW, SH, float(P["screen_radius_px"]), FORM["bg"])
    CX, CWD, CL = PX, SW - 2 * CARD_SIDE, SX0 + CARD_SIDE
    LX = CL + TEXT_SIDE
    y = SY0 + TOP_PAD
    th = TITLE_CARD_H
    pbox("tcard", CX, y + th / 2, CWD, th, 10.0, C["paper"])
    pbox("ttop", CX, y + 5, CWD, 10.0, 5.0, FORM["topbar"])
    title1 = ptext("title1", "2026 남성중학교 방송부", "Regular", FS["title"], LX, y + 46, FORM["text"])
    title2 = ptext("title2", "신청곡 신청", "Regular", FS["title"], LX, y + 82, FORM["text"])
    pubs += [(title1, "제목 1"), (title2, "제목 2")]
    for i, s in enumerate(("부적절한 신청곡은 거부될 수 있으며, 불이익을 받을 수", "있습니다. 안전한 방송을 위해 이메일 및 학번, 이름을",
                           "수집하며, 해당 정보는 방송부 내부에서만 처리됩니다.")):
        pubs.append((ptext("desc", s, "Regular", FS["desc"], LX, y + 118 + i * 20, FORM["text"]), "설명 %d" % (i + 1)))
    pbox("rule", CX, y + 182, CWD, 1.0, 0.0, FORM["line"])
    pubs.append((ptext("req", "* 표시는 필수 질문임", "Regular", FS["req"], LX, y + 203, FORM["red"]), "필수 안내"))
    y += th + CARD_GAP
    taps = []
    yy = [y]
    placeholder = []

    def question_card(label, qh, pub):
        top = yy[0]
        pbox("qcard", CX, top + qh / 2, CWD, qh, 10.0, C["paper"])
        pubs.append((ptext("qlabel", label, "Medium", FS["label"], LX, top + 35, FORM["text"]), pub))
        yy[0] += qh + CARD_GAP
        return top

    def checkbox(top, s, f_on, pub):
        bx, by = LX + 12, top + 78
        pbox("cbb", bx, by, 24.0, 24.0, 3.0, FORM["gray"])
        pbox("cbh", bx, by, 20.0, 20.0, 2.0, C["paper"])
        on = {0: 0.0, f_on - 1: 0.0, f_on + 2: 1.0}
        pbox("cbon", bx, by, 24.0, 24.0, 3.0, FORM["accent"], blend=on)
        ptext("tick", "✓", "Regular", FS["tick"], bx, by + 1, C["paper"], align=0, blend=on, font="Segoe UI Symbol")
        pubs.append((ptext("cbtext", s, "Regular", FS["body"], bx + 26, by, FORM["text"]), pub))
        taps.append((bx, by, f_on))

    def answer(top, s, f0, f1, blur_at, pub):
        ly = top + 100
        pbox("aline", LX + 160, ly, 320.0, 1.5, 0.0, FORM["line"])
        pbox("afocus", LX + 160, ly, 320.0, 3.0, 0.0, FORM["accent"], blend={0: 0.0, f0 - 3: 0.0, f0: 1.0, blur_at: 1.0, blur_at + 3: 0.0})
        placeholder.append(ptext("aph", "내 답변", "Regular", FS["body"], LX, ly - 17, FORM["light"], blend={0: 1.0, f0 - 1: 1.0, f0: 0.0}))
        pubs.append((ptext("ans", s, "Regular", FS["answer"], LX, ly - 17, FORM["text"], write={0: 0.0, f0: 0.0, f1: 1.0}), pub))
        taps.append((LX + 160, ly - 17, f0 - 3))

    q1 = question_card("이메일 *", 112.0, "문항 1")
    checkbox(q1, "응답과 함께 이메일 주소 기록", FR["tap1"], "체크 1")
    q2 = question_card("신청곡 *", 124.0, "문항 2")
    answer(q2, "노는게 제일 좋아 - 뽀로로", FR["type2"], FR["type2_end"], FR["type3"] - 3, "답 2")
    q3 = question_card("학번이름(예 : 10101 홍길동) *", 124.0, "문항 3")
    answer(q3, "10101 김방송", FR["type3"], FR["type3_end"], FR["tap4"] - 1, "답 3")
    q4 = question_card("익명으로 해드릴까요?", 112.0, "문항 4")
    checkbox(q4, "익명으로 해주세요", FR["tap4"], "체크 4")
    bx, by = LX + 44, yy[0] + 26
    pbox("submit", bx, by, 88.0, 42.0, 5.0, FORM["accent"])
    pbox("press", bx, by, 88.0, 42.0, 5.0, (0, 0, 0), blend={0: 0.0, FR["submit"] - 1: 0.0, FR["submit"]: 0.22, FR["submit"] + 6: 0.0})
    pubs.append((ptext("submit", "제출", "Medium", FS["button"], bx, by, C["paper"], align=0), "버튼"))
    pubs.append((ptext("clear", "양식 지우기", "Medium", FS["clear"], CL + CWD - 20, by, FORM["accent"], align=1), "지우기"))
    taps.append((bx, by, FR["submit"] - 2))
    tap_rgb = fusion_color("#1A1A1A")
    for tx, ty, tf in taps:
        k = key("tap")
        e = m.add(fu.ellipse("th_E" + k, X(tx), 1 - Y(ty), X(54.0), X(54.0)))
        s = m.add(fu.solid("th_" + k, tap_rgb, e.name))
        anim(ct.over(s.name), k, {0: 0.0, tf - 2: 0.0, tf: 0.28, tf + 8: 0.0})
    # 완료 화면 — 제목 두 줄은 폼 화면의 글자를 그대로 다시 얹는다
    done = {0: 0.0, FR["done"] - 1: 0.0, FR["done"]: 1.0}
    pbox("dbg", PX, PY, SW, SH, float(P["screen_radius_px"]), FORM["bg"], blend=done)
    dy = SY0 + TOP_PAD
    pbox("dcard", CX, dy + DONE_CARD_H / 2, CWD, DONE_CARD_H, 10.0, C["paper"], blend=done)
    pbox("dtop", CX, dy + 5, CWD, 10.0, 5.0, FORM["topbar"], blend=done)
    again(title1, done)
    again(title2, done)
    pubs.append((ptext("dmsg", "응답이 기록되었습니다.", "Regular", FS["body"], LX, dy + 130, FORM["text"], blend=done), "완료 문구"))
    pubs.append((ptext("dlink", "다른 응답 제출", "Regular", FS["clear"], LX, dy + 172, FORM["accent"], blend=done), "완료 링크"))
    pbox("notch", PX, SY0 + 20, 120.0, 26.0, 13.0, FORM["phone"])
    pubs.append((ptext("clock", "12:30", "SemiBold", FS["clock"], SX0 + 34, SY0 + 21, FORM["text"]), "시계"))
    # 오른쪽 안내 카드(카드 규칙, 알약 1.25배)
    RC = F["card"]
    L, Tp = float(RC["left_px"]), float(RC["top_px"])
    CW2, CH2 = map(float, RC["size_px"])
    r, b = CARD["radius_px"], CARD["border_px"]
    ccx, ccy = L + CW2 / 2, Tp + CH2 / 2
    ro = m.add(fu.rect("th_Rrc", X(ccx), 1 - Y(ccy), X(CW2), Y(CH2), r / (CH2 / 2.0)))
    ri = m.add(fu.rect("th_Rrci", X(ccx), 1 - Y(ccy), X(CW2 - 2 * b), Y(CH2 - 2 * b), (r - b) / ((CH2 - 2 * b) / 2.0)))
    ct.over(solid_ref(m, "th_rc_c", ref, ro.name).name)
    ct.over(m.add(fu.solid("th_rc_w", C["paper"], ri.name)).name)
    s = CARD["pill_scale"]
    tn, ti, ta = pills(m, ct, "rc", L + LAY["card_pill"]["inset_px"] * s, 1 - Y(Tp - LAY["card_pill"]["lift_px"] * s), s, ref, name="신청 안내")
    lines = []
    for i, ln in enumerate(RC["lines"], 1):
        k = "r%d" % i
        t = fu.text("th_" + k, ln["text"], DISPLAY["family"], DISPLAY["style"], ln["size"], X(ccx), 1 - Y(ln["y_px"]),
                    (0, 0, 0) if ln["accent"] else C["ink"])
        if ln["accent"]:
            text_ref(t, ref)
        m.add(t)
        fit_text(m, ct, t, k, (X(ccx), 1 - Y(ln["y_px"])), CW2 - 2 * RC["pad_px"])
        lines.append(t)
    fm = st.over(ct.cur, blend=1, blend_expr=fexp)
    for t, label in pubs:
        m.publish(t.name, "StyledText", name=label)
    for i, t in enumerate(placeholder, 1):
        m.publish(t.name, "StyledText", name="빈칸 %d" % i)
    for i, t in enumerate(lines, 1):
        m.publish(t.name, "StyledText", name="안내 %d" % i)
    card_publish(m, wall_m, (tn, ti, ta), ref, fm)
    return finish(m, st)


ELEMENTS = [("th01 폼 데모", form_demo, 227)]
