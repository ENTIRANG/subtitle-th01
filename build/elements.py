# -*- coding: utf-8 -*-
"""th01 요소 → Fusion 매크로. 값은 tokens.json 에서만 온다. 글자에 따라 변하는 폭·위치는 전부 퓨전 표현식(DataWindow).

순환 금지: 폭을 재는 글자(DataWindow 를 읽히는 Text+)의 Center·Size 는 고정한다. 옮기기·줄이기는 Text+ 바로 뒤의
Transform 이 맡는다(place_text, fit_text). 글자가 자기 폭에서 나온 값을 따르면 Fusion 이 프레임을 끝내지 못하고 멈춘다.

색 설정: set_pipeline("cm") 은 기준 설정(색 관리 v2, Rec.709 Scene) 값, set_pipeline("yrgb") 는 색 관리 없는 프로젝트용 값."""
import os, json, re
import fu

HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "..", "tokens.json"), encoding="utf-8"))
S, BAR, PILL, CARD, BOX, LAY = T["size"], T["bar"], T["pill"], T["card"], T["box"], T["layout"]
DISPLAY, LABEL, ICON = T["font"]["display"], T["font"]["label"], T["font"]["icon"]
BAR_W_PX = BAR["outer"]["width"] * 1920      # 자막바·카드 폭 1546px — 글자 줄이 넘지 않을 자리
QR = LAY["qr"]
QR_COL_PX = float(QR["column_width_px"])
OE = T["pipeline"]["oetf"]


# ───────────── 색 설정 ─────────────
def oetf(v):
    """BT.709 OETF — 기준 설정(Rec.709 Scene) 값을 색 관리 없는 프로젝트의 화면 값으로."""
    return OE["linear"] * v if v < OE["beta"] else OE["alpha"] * v ** OE["gamma"] - (OE["alpha"] - 1)


def inv_oetf(v):
    """BT.709 OETF 역함수 — 화면색을 기준 설정 값으로."""
    return v / OE["linear"] if v < OE["linear"] * OE["beta"] else ((v + OE["alpha"] - 1) / OE["alpha"]) ** (1 / OE["gamma"])


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5))


PIPE = {"name": "cm"}
C = {}                                        # 지금 빌드하는 색 설정의 Fusion 색값(set_pipeline 이 채운다)


def fusion_color(spec, pipe=None):
    """tokens 색 → Fusion 값. 목록 = 기준 설정 값(원본 그대로), {"display": "#hex"} 또는 "#hex" = 화면색."""
    pipe = pipe or PIPE["name"]
    if isinstance(spec, str) or isinstance(spec, dict):
        rgb = hex_rgb(spec if isinstance(spec, str) else spec["display"])
        return tuple(inv_oetf(v) for v in rgb) if pipe == "cm" else rgb
    return tuple(float(v) for v in spec) if pipe == "cm" else tuple(oetf(float(v)) for v in spec)


def set_pipeline(pipe):
    PIPE["name"] = pipe
    C.clear()
    C.update({k: fusion_color(v, pipe) for k, v in T["color"].items()})


set_pipeline("cm")


def X(px):
    return px / 1920.0


def Y(px):
    return px / 1080.0


def n(v):
    """표현식 안에 넣을 숫자."""
    return fu._num(v)


def dw(tool):
    """글자 폭(1920 폭 기준 픽셀). DataWindow 는 타임라인 해상도의 픽셀이라 이미지 폭으로 나눠 1920 기준으로 맞춘다
    — UHD·720p 타임라인에서도 알약·상자 비율이 같다."""
    o = "%s.Output[time]" % tool
    return "((%s.DataWindow[3]-%s.DataWindow[1])*1920/%s.Width)" % (o, o, o)


def color_master(m, name, rgb):
    """색을 쥐는 노드(화면에 안 나감). 다른 노드는 표현식으로 이 값을 따른다."""
    t = m.add(fu.solid(name, rgb))
    return name


def solid_ref(m, name, ref, mask):
    t = m.add(fu.solid(name, (0, 0, 0), mask))
    for ch in ("Red", "Green", "Blue"):
        t.set("TopLeft" + ch, 0, "%s.TopLeft%s" % (ref, ch))
    return t


def text_ref(t, ref):
    for i, ch in enumerate(("Red", "Green", "Blue")):
        t.set(ch + "1", 0, "%s.TopLeft%s" % (ref, ch))
    return t


class Stack(object):
    """Merge 로 차례로 쌓기."""

    def __init__(self, m, base):
        self.m, self.cur, self.i = m, base, 0

    def over(self, fg, blend=None, blend_expr=None, center=None, size_expr=None):
        self.i += 1
        t = self.m.add(fu.merge("%s_m%d" % (self.m.prefix, self.i), self.cur, fg, blend, blend_expr, center, size_expr))
        self.cur = t.name
        return t


def macro(name):
    m = fu.Macro(name)
    m.prefix = "th"
    return m


def finish(m, stack, publish_xf=True):
    xf = fu.Tool("th_xf", "Transform")
    xf.link("Input", stack.cur)
    m.add(xf)
    m.output = "th_xf"
    if publish_xf:
        m.publish("th_xf", "Center", name="위치", page="Controls")
        m.publish("th_xf", "Size", name="크기", default=1)
    return m


def fit(m, src, key, pivot, avail_px, width_expr):
    """글자가 길어 자리(avail_px)를 넘으면 그 줄을 통째로 줄인다. 넘지 않으면 배율 1(기본 모양 그대로).
    width_expr 는 줄의 Fusion 폭(0~1) 표현식. 글자 자신이 아니라 뒤의 Transform 이 줄이므로 순환이 없다."""
    t = fu.Tool("th_fit%s" % key, "Transform")
    t.link("Input", src)
    t.set("Pivot", list(pivot))
    t.set("Size", 1, "min(1,%s/(%s))" % (n(X(avail_px)), width_expr))
    return m.add(t)


def fit_text(m, stack, t, key, pivot, avail_px):
    """글자 한 줄: 폭 = 글자 DataWindow."""
    stack.over(fit(m, t.name, key, pivot, avail_px, "%s/1920" % dw(t.name)).name)


def shrink(dw_expr, avail_px):
    """글자 배율: 글자 폭(px)이 avail_px 를 넘을 때만 1 보다 작아진다."""
    return "min(1,%s/%s)" % (n(avail_px), dw_expr)


def place_text(m, stack, t, key, cy, k_expr, cx_expr):
    """제자리(가운데 0.5)에 고정한 글자 t 를 배율 k 로 줄여 가운데를 cx_expr 에 둔다.
    Transform 은 Text+ 바로 뒤에 붙인다 — 줄이기 전 글자가 화면 밖으로 나가도 잘리지 않는다.
    상자는 줄이지 않는다(높이·곡률 고정, 폭만 글자에 맞춘다)."""
    tr = fu.Tool("th_tx%s" % key, "Transform")
    tr.link("Input", t.name)
    tr.set("Pivot", [0.5, cy])
    tr.set("Size", 1, k_expr)
    tr.set("Center", [0.5, 0.5], "Point(%s,0.5)" % cx_expr)
    m.add(tr)
    stack.over(tr.name)
    return tr


def expr_or(v):
    return v if isinstance(v, str) else n(v)


# ───────────── 바 모양 상자(자막바와 같은 높이·곡률) ─────────────
def barbox(m, st, key, cx, cy, w, ref, fill=None):
    """cx, w 는 숫자 또는 표현식(Fusion 단위). 바깥 색 + 안쪽 흰 면(6px 안). 높이·곡률은 자막바(tokens bar)와 같다."""
    b = BAR["border_px"]
    ro = m.add(fu.rect("th_R%s" % key, 0.5, cy, 0.1, BAR["outer"]["height"], BAR["outer"]["corner"]))
    ri = m.add(fu.rect("th_R%si" % key, 0.5, cy, 0.1, BAR["inner"]["height"], BAR["inner"]["corner"]))
    if isinstance(w, str):
        ro.set("Width", 0.1, w)
        ri.set("Width", 0.1, "th_R%s.Width-%s" % (key, n(X(2 * b))))
    else:
        ro.set("Width", w)
        ri.set("Width", w - X(2 * b))
    if isinstance(cx, str):
        ro.set("Center", [0.5, cy], "Point(%s,%s)" % (cx, n(cy)))
        ri.set("Center", [0.5, cy], "Point(th_R%s.Center.X,%s)" % (key, n(cy)))
    else:
        ro.set("Center", [cx, cy])
        ri.set("Center", [cx, cy])
    c = solid_ref(m, "th_%s_c" % key, ref, ro.name)
    st.over(c.name)
    wbg = m.add(fu.solid("th_%s_w" % key, fill or C["paper"], ri.name))
    st.over(wbg.name)
    return ro


# ───────────── 이름·소속 알약(자막바·카드 공통, 배율 s) ─────────────
def pills(m, st, key, left_px, cy, s, ref, name="방송부원", icon="♪", affil="NSBD"):
    P = PILL
    ho, hi = Y(P["height"] * 1080 * s), Y(P["inner_height"] * 1080 * s)
    left = X(left_px)
    # 이름 글자(알약 가운데)
    tn = m.add(fu.text("th_%sname" % key, name, LABEL["family"], LABEL["style"], S["pill-name"] * s, 0.5, cy, C["paper"]))
    rn = m.add(fu.rect("th_R%sname" % key, 0.5, cy, 0.1, ho, 1.0))
    rn.set("Width", 0.1, "(%s+%s)/1920" % (dw(tn.name), n(2 * P["name_pad_px"] * s)))
    rn.set("Center", [0.5, cy], "Point(%s+th_R%sname.Width/2,%s)" % (n(left), key, n(cy)))
    st.over(solid_ref(m, "th_%sname_c" % key, ref, rn.name).name)
    st.over(tn.name, center="Point(th_R%sname.Center.X,0.5)" % key)
    # 소속 알약: 이름 알약 끝 + 16px 부터, 아이콘 +34, 글자 +69, 오른쪽 35
    ta = m.add(text_ref(fu.text("th_%saffil" % key, affil, LABEL["family"], LABEL["style"], S["pill-affil"] * s, 0.5, cy, (0, 0, 0)), ref))
    ra = m.add(fu.rect("th_R%saff" % key, 0.5, cy, 0.1, ho, 1.0))
    ra.set("Width", 0.1, "(%s+%s)/1920" % (dw(ta.name), n((P["affil_text_px"] + P["affil_right_px"]) * s)))
    aleft = "th_R%sname.Center.X+th_R%sname.Width/2+%s" % (key, key, n(X(P["gap_px"] * s)))
    ra.set("Center", [0.5, cy], "Point(%s+th_R%saff.Width/2,%s)" % (aleft, key, n(cy)))
    rai = m.add(fu.rect("th_R%saffi" % key, 0.5, cy, 0.1, hi, 1.0))
    rai.set("Width", 0.1, "th_R%saff.Width-%s" % (key, n(X(2 * P["affil_border_px"] * s))))
    rai.set("Center", [0.5, cy], "Point(th_R%saff.Center.X,%s)" % (key, n(cy)))
    aL = "th_R%saff.Center.X-th_R%saff.Width/2" % (key, key)
    ti = m.add(text_ref(fu.text("th_%sicon" % key, icon, ICON["family"], ICON["style"], S["pill-icon"] * s, 0.5, cy, (0, 0, 0)), ref))
    icy = cy + (PILL["icon_center_y"] - PILL["center_y"]) * s
    ti.set("Center", [0.5, icy], "Point(%s+%s,%s)" % (aL, n(X(P["affil_icon_px"] * s)), n(icy)))
    st.over(solid_ref(m, "th_%saff_c" % key, ref, ra.name).name)
    st.over(m.add(fu.solid("th_%saff_w" % key, C["paper"], rai.name)).name)
    st.over(ti.name)
    st.over(ta.name, center="Point(%s+%s+%s/1920/2,0.5)" % (aL, n(X(P["affil_text_px"] * s)), dw(ta.name)))
    return tn, ti, ta


# ───────────── 1. 자막바 ─────────────
def subtitle_bar():
    m = macro("th01_SubtitleBar")
    ref = color_master(m, "th_color", C["speaker-1"])
    st = Stack(m, m.add(fu.canvas("th_canvas")).name)
    cx, cy = BAR["center"]
    ro = m.add(fu.rect("th_Rbar", cx, cy, BAR["outer"]["width"], BAR["outer"]["height"], BAR["outer"]["corner"]))
    ri = m.add(fu.rect("th_Rbari", cx, cy, BAR["inner"]["width"], BAR["inner"]["height"], BAR["inner"]["corner"]))
    st.over(solid_ref(m, "th_bar_c", ref, ro.name).name)
    st.over(m.add(fu.solid("th_bar_w", C["paper"], ri.name)).name)
    tn, ti, ta = pills(m, st, "", PILL["name_left_px"], PILL["center_y"], 1.0, ref)
    m.publish(tn.name, "StyledText", name="이름")
    m.publish(ti.name, "StyledText", name="아이콘")
    m.publish(ta.name, "StyledText", name="소속")
    m.publish_color(ref, "색", 1, C["speaker-1"])
    return finish(m, st)


# ───────────── 2. 자막 ─────────────
def caption():
    m = macro("th01_Caption")
    st = Stack(m, m.add(fu.canvas("th_canvas")).name)
    t = m.add(fu.text("th_text", "여러분이 신청한 음악을 틀어드려요", DISPLAY["family"], DISPLAY["style"], S["caption"], BAR["caption_center"][0], BAR["caption_center"][1], C["ink"]))
    fit_text(m, st, t, "", BAR["caption_center"], BAR_W_PX - 2 * BOX["pad_px"])
    m.publish(t.name, "StyledText", name="자막")
    m.publish(t.name, "Red1", name="글자색", group=2, default=C["ink"][0])
    m.publish(t.name, "Green1", group=2, default=C["ink"][1])
    m.publish(t.name, "Blue1", group=2, default=C["ink"][2])
    return finish(m, st)


# ───────────── 3. 질문(Q 배지 + 파트 + 질문) ─────────────
def question():
    m = macro("th01_Question")
    ref = color_master(m, "th_color", C["speaker-3"])
    st = Stack(m, m.add(fu.canvas("th_canvas")).name)
    Q = LAY["question"]
    left = X(Q["left_px"])
    h, gap_px = float(Q["height_px"]), Q["row_gap_px"]
    y1, y2 = 1 - Y(Q["top_px"] + h / 2), 1 - Y(Q["top_px"] + h + gap_px + h / 2)
    pad = Q["pad_px"]
    # Q 배지(정사각, 바와 같은 곡률)
    rq = m.add(fu.rect("th_Rq", left + X(h / 2), y1, X(h), Y(h), BAR["outer"]["corner"]))
    st.over(solid_ref(m, "th_q_c", ref, rq.name).name)
    tq = m.add(fu.text("th_qmark", "Q.", DISPLAY["family"], DISPLAY["style"], S["caption"], left + X(h / 2), y1 + Y(Q["badge_text_dy_px"]), C["paper"]))
    st.over(tq.name)
    # 파트 상자 — 자리는 바 폭에서 배지(110 + 16)를 뺀 것
    tp = m.add(fu.text("th_part", "방송부가 궁금한 거 다 물어봤다", DISPLAY["family"], DISPLAY["style"], S["question"], 0.5, y1, C["ink"]))
    kp = shrink(dw(tp.name), BAR_W_PX - (h + gap_px) - 2 * pad)
    barbox(m, st, "part", "%s+th_Rpart.Width/2" % n(left + X(h + gap_px)), y1, "(%s*%s+%s)/1920" % (dw(tp.name), kp, n(2 * pad)), ref)
    place_text(m, st, tp, "part", y1, kp, "th_Rpart.Center.X")
    # 질문 상자(둘째 줄) — 따로 쌓아서 보이기/숨기기
    st2 = Stack(m, m.add(fu.canvas("th_canvas2")).name)
    st2.i = 100
    tqq = m.add(fu.text("th_quest", "롯데 응원한 지 얼마나 되셨나요?", DISPLAY["family"], DISPLAY["style"], S["question"], 0.5, y2, C["ink"]))
    kq = shrink(dw(tqq.name), BAR_W_PX - 2 * pad)
    barbox(m, st2, "quest", "%s+th_Rquest.Width/2" % n(left), y2, "(%s*%s+%s)/1920" % (dw(tqq.name), kq, n(2 * pad)), ref)
    place_text(m, st2, tqq, "quest", y2, kq, "th_Rquest.Center.X")
    row2 = st.over(st2.cur, blend=1)
    m.publish(tp.name, "StyledText", name="파트")
    m.publish(tqq.name, "StyledText", name="질문")
    m.publish(row2.name, "Blend", name="질문 줄", default=1)
    m.publish_color(ref, "색", 1, C["speaker-3"])
    return finish(m, st)


# ───────────── 4. 이지선다(A/B) ─────────────
def two_choice():
    m = macro("th01_TwoChoice")
    refA = color_master(m, "th_colorA", C["speaker-3"])
    refB = color_master(m, "th_colorB", C["speaker-2"])
    st = Stack(m, m.add(fu.canvas("th_canvas")).name)
    CH = LAY["choice"]
    cy = 1 - Y(CH["y_px"])
    circ, lead, pad, gap = float(CH["circle_px"]), float(CH["lead_px"]), float(CH["pad_px"]), float(CH["gap_px"])
    tA = m.add(fu.text("th_textA", "롯데 우승", DISPLAY["family"], DISPLAY["style"], S["choice"], 0.5, cy, C["ink"]))
    tB = m.add(fu.text("th_textB", "우리 반 기말 1등", DISPLAY["family"], DISPLAY["style"], S["choice"], 0.5, cy, C["ink"]))
    dmax = "max(%s,%s)" % (dw(tA.name), dw(tB.name))
    k = shrink(dmax, (BAR_W_PX - gap) / 2 - lead - pad)      # 두 상자 + 간격이 바 폭 안에
    wexp = "(%s*%s+%s)/1920" % (dmax, k, n(lead + pad))
    blends = []
    for key, ref, t, letter, sign in (("A", refA, tA, "A", -1), ("B", refB, tB, "B", 1)):
        s2 = Stack(m, m.add(fu.canvas("th_canvas%s" % key)).name)
        s2.i = 100 if key == "A" else 200
        cx = "0.5%s(th_R%s.Width/2+%s)" % ("-" if sign < 0 else "+", key, n(X(gap / 2)))
        barbox(m, s2, key, cx, cy, wexp, ref)
        L = "th_R%s.Center.X-th_R%s.Width/2" % (key, key)
        e = m.add(fu.ellipse("th_E%s" % key, 0.5, cy, X(circ), X(circ)))
        e.set("Center", [0.5, cy], "Point(%s+%s,%s)" % (L, n(X(CH["circle_inset_px"] + circ / 2)), n(cy)))
        s2.over(solid_ref(m, "th_%s_dot" % key, ref, e.name).name)
        tl = m.add(fu.text("th_letter%s" % key, letter, DISPLAY["family"], DISPLAY["style"], S["choice"], 0.5, cy, C["paper"]))
        tl.set("Center", [0.5, cy], "Point(th_E%s.Center.X,%s)" % (key, n(cy)))
        s2.over(tl.name)
        place_text(m, s2, t, key, cy, k, "%s+%s+%s*%s/1920/2" % (L, n(X(lead)), dw(t.name), k))
        blends.append((key, st.over(s2.cur, blend=1)))
    m.publish(tA.name, "StyledText", name="A")
    m.publish(tB.name, "StyledText", name="B")
    m.publish(blends[0][1].name, "Blend", name="A 선명도", default=1)
    m.publish(blends[1][1].name, "Blend", name="B 선명도", default=1)
    m.publish_color(refA, "A 색", 1, C["speaker-3"])
    m.publish_color(refB, "B 색", 2, C["speaker-2"])
    return finish(m, st)


# ───────────── 카드 공통 ─────────────
def fade_controls(m):
    c = m.add(fu.canvas("th_ctl"))
    c.user_controls = {"FadeIn": fu.user_number("Fade In", T["fade"]["card_content_frames"]),
                       "FadeOut": fu.user_number("Fade Out", T["fade"]["card_content_frames"])}
    c.set("FadeIn", T["fade"]["card_content_frames"]).set("FadeOut", T["fade"]["card_content_frames"])
    return "iif(th_ctl.FadeIn<1,1,min(1,time/th_ctl.FadeIn))*iif(th_ctl.FadeOut<1,1,min(1,(comp.RenderEnd-time)/th_ctl.FadeOut))"


def card_base(m, ref, hpx, name="신청 안내"):
    """벽(켜고 끌 수 있음) + 카드 틀 + 알약. (전체 스택, 카드 내용 스택, 카드 윗선 y) 반환."""
    st = Stack(m, m.add(fu.canvas("th_canvas")).name)
    wall = m.add(fu.gradient_v("th_wall", C["wall-top"], C["wall-bottom"]))
    wall_m = st.over(wall.name, blend=1)
    content = Stack(m, m.add(fu.canvas("th_canvas_c")).name)
    content.i = 100
    cx, cy = CARD["center"]
    w, h, r, b = CARD["width"], hpx, CARD["radius_px"], CARD["border_px"]
    ro = m.add(fu.rect("th_Rcard", cx, cy, w, Y(h), r / (h / 2.0)))
    ri = m.add(fu.rect("th_Rcardi", cx, cy, w - X(2 * b), Y(h - 2 * b), (r - b) / ((h - 2 * b) / 2.0)))
    content.over(solid_ref(m, "th_card_c", ref, ro.name).name)
    content.over(m.add(fu.solid("th_card_w", C["paper"], ri.name)).name)
    s = CARD["pill_scale"]
    left_px = (0.5 - w / 2) * 1920 + LAY["card_pill"]["inset_px"] * s
    top_px = (1 - cy) * 1080 - h / 2
    pcy = 1 - Y(top_px - LAY["card_pill"]["lift_px"] * s)
    tn, ti, ta = pills(m, content, "p", left_px, pcy, s, ref, name=name)
    return st, wall_m, content, (tn, ti, ta)


def card_publish(m, wall_m, pills_t, ref, fade_merge):
    tn, ti, ta = pills_t
    m.publish(tn.name, "StyledText", name="이름 알약")
    m.publish(ti.name, "StyledText", name="아이콘")
    m.publish(ta.name, "StyledText", name="소속 알약")
    m.publish_color(ref, "색", 1, C["speaker-3"])
    m.publish(wall_m.name, "Blend", name="벽", default=1)
    m.publish("th_ctl", "FadeIn", name="내용 페이드 인(프레임)")
    m.publish("th_ctl", "FadeOut", name="내용 페이드 아웃(프레임)")


# ───────────── 5. 안내 카드 ─────────────
def info_card():
    m = macro("th01_InfoCard")
    ref = color_master(m, "th_color", C["speaker-3"])
    fexp = fade_controls(m)
    st, wall_m, content, pl = card_base(m, ref, CARD["height_px"])
    t1 = m.add(fu.text("th_line1", "신청 방법이 바뀌었어요!", DISPLAY["family"], DISPLAY["style"], S["card-line-1"], 0.5, CARD["line1_y"], C["ink"]))
    t2 = m.add(text_ref(fu.text("th_line2", "오프라인 신청은 이제 없어요", DISPLAY["family"], DISPLAY["style"], S["card-line-2"], 0.5, CARD["line2_y"], (0, 0, 0)), ref))
    fit_text(m, content, t1, "1", (0.5, CARD["line1_y"]), BAR_W_PX - 2 * BOX["pad_px"])
    fit_text(m, content, t2, "2", (0.5, CARD["line2_y"]), BAR_W_PX - 2 * BOX["pad_px"])
    fm = st.over(content.cur, blend=1, blend_expr=fexp)
    m.publish(t1.name, "StyledText", name="큰 줄")
    m.publish(t2.name, "StyledText", name="작은 줄")
    card_publish(m, wall_m, pl, ref, fm)
    return finish(m, st)


# ───────────── 6. 링크 ─────────────
def link_box():
    m = macro("th01_Link")
    ref = color_master(m, "th_color", C["speaker-3"])
    st = Stack(m, m.add(fu.canvas("th_canvas")).name)
    cy = 1 - Y(LAY["link"]["y_px"])
    t = m.add(fu.text("th_link", "link.trh.kr/nsbd", DISPLAY["family"], DISPLAY["style"], S["link"], 0.5, cy, C["ink"]))
    k = shrink(dw(t.name), BAR_W_PX - 2 * BOX["pad_px"])
    barbox(m, st, "link", 0.5, cy, "(%s*%s+%s)/1920" % (dw(t.name), k, n(2 * BOX["pad_px"])), ref)
    place_text(m, st, t, "link", cy, k, "0.5")
    m.publish(t.name, "StyledText", name="링크")
    m.publish_color(ref, "색", 1, C["speaker-3"])
    return finish(m, st)


# ───────────── 7. QR 카드 ─────────────
def qr_card():
    m = macro("th01_QrCard")
    ref = color_master(m, "th_color", C["speaker-3"])
    fexp = fade_controls(m)
    st, wall_m, content, pl = card_base(m, ref, CARD["tall_height_px"])
    ld = m.add(fu.loader("th_qr", ""))
    # QR 을 정사각 자리(1920 기준 image_px)에 맞춘다 — Merge 배율이라 키워도 안 잘린다.
    # 이미지가 없으면 배율 1(Lua 의 and/or 는 앞이 nil 이면 뒤를 계산하지 않는다)
    o = "th_qr.Output[time]"
    qsize = "(%s and %s*th_canvas.Output[time].Width/1920/max(%s.Width,%s.Height)) or 1" % (o, n(QR["image_px"]), o, o)
    qx, qy = QR["image_center_px"]
    content.over(ld.name, center=(X(qx), 1 - Y(qy)), size_expr=qsize)
    cx = X(QR["column_x_px"])
    y1, y2, yn = 1 - Y(QR["line1_y_px"]), 1 - Y(QR["line2_y_px"]), 1 - Y(QR["note_y_px"])
    t1 = m.add(fu.text("th_line1", "QR을 찍거나", DISPLAY["family"], DISPLAY["style"], S["link"], cx, y1, C["ink"]))
    t2 = m.add(fu.text("th_line2", "링크로 들어오세요", DISPLAY["family"], DISPLAY["style"], S["link"], cx, y2, C["ink"]))
    fit_text(m, content, t1, "1", (cx, y1), QR_COL_PX)
    fit_text(m, content, t2, "2", (cx, y2), QR_COL_PX)
    ly = 1 - Y(QR["link_y_px"])
    tl = m.add(fu.text("th_link", "link.trh.kr/nsbd", DISPLAY["family"], DISPLAY["style"], S["link"], cx, ly, C["ink"]))
    tl.set("Center", [0.5, ly])                               # 제자리 고정, 옮기기는 place_text
    k = shrink(dw(tl.name), QR_COL_PX - 2 * BOX["pad_px"])
    barbox(m, content, "link", cx, ly, "(%s*%s+%s)/1920" % (dw(tl.name), k, n(2 * BOX["pad_px"])), ref)
    place_text(m, content, tl, "link", ly, k, n(cx))
    tn = m.add(fu.text("th_note", "학교 곳곳 신청곡 포스터에도 있어요", DISPLAY["family"], DISPLAY["style"], S["card-note"], cx, yn, C["muted"]))
    fit_text(m, content, tn, "n", (cx, yn), QR_COL_PX)
    fm = st.over(content.cur, blend=1, blend_expr=fexp)
    m.publish(t1.name, "StyledText", name="큰 줄 1")
    m.publish(t2.name, "StyledText", name="큰 줄 2")
    m.publish(tl.name, "StyledText", name="링크")
    m.publish(tn.name, "StyledText", name="보조 줄")
    m.publish(ld.name, "Clip", name="QR 이미지")
    card_publish(m, wall_m, pl, ref, fm)
    return finish(m, st)


ELEMENTS = [
    ("th01 자막바", subtitle_bar, 150),
    ("th01 자막", caption, 90),
    ("th01 질문", question, 150),
    ("th01 이지선다", two_choice, 150),
    ("th01 안내 카드", info_card, 120),
    ("th01 링크", link_box, 120),
    ("th01 QR 카드", qr_card, 226),
]
