# -*- coding: utf-8 -*-
"""Fusion .setting(매크로) 쓰기 도구.

Lua 표 직렬화 + 노드 생성 + 매크로 조립. 값은 전부 Fusion 단위다:
위치 Center = (x, y) 0~1(y 는 아래에서 위), 마스크 Width = 픽셀/1920, Height = 픽셀/1080,
CornerRadius = 모서리 반지름 / (짧은 변/2), Text+ Size = Fusion 글자 크기.
"""
from collections import OrderedDict

W, H = 1920.0, 1080.0


# ───────────── Lua 직렬화 ─────────────
class Raw(str):
    """그대로 쓰는 Lua 조각."""


class Typed(object):
    """Input { ... }, FuID { ... }, Merge { ... } 처럼 이름 붙은 표."""

    def __init__(self, kind, body, ordered=False):
        self.kind, self.body, self.ordered = kind, body, ordered


def fuid(s):
    return Typed("FuID", [s])


def _key(k):
    if isinstance(k, Raw):                      # [0] 같은 숫자 키(스플라인 KeyFrames)는 그대로
        return str(k)
    if isinstance(k, str) and k.replace("_", "a").isalnum() and not k[0].isdigit() and k.isascii():
        return k
    return '["%s"]' % str(k).replace("\\", "\\\\").replace('"', '\\"')


def _num(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    s = repr(float(v))
    return s[:-2] if s.endswith(".0") else s


def lua(v, ind=0):
    t = "\t" * ind
    if isinstance(v, Raw):
        return str(v)
    if isinstance(v, bool) or isinstance(v, (int, float)):
        return _num(v)
    if isinstance(v, str):
        return '"%s"' % v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    if isinstance(v, Typed):
        return v.kind + " " + lua(v.body if not v.ordered else Ordered(v.body), ind)
    if isinstance(v, Ordered):
        return "ordered() " + lua(OrderedDict(v.items_), ind)
    if isinstance(v, (list, tuple)):
        if all(isinstance(x, (int, float, str)) and not isinstance(x, bool) for x in v) and len(v) <= 4:
            return "{ " + ", ".join(lua(x) for x in v) + " }"
        return "{\n" + "".join("%s\t%s,\n" % (t, lua(x, ind + 1)) for x in v) + t + "}"
    if isinstance(v, dict):
        if not v:
            return "{ }"
        return "{\n" + "".join("%s\t%s = %s,\n" % (t, _key(k), lua(x, ind + 1)) for k, x in v.items()) + t + "}"
    raise TypeError(type(v))


class Ordered(object):
    def __init__(self, items):
        self.items_ = list(items.items()) if isinstance(items, dict) else list(items)


# ───────────── 입력 ─────────────
def inp(value=None, expr=None, src=None, out="Output"):
    d = OrderedDict()
    if src is not None:
        d["SourceOp"] = src
        d["Source"] = out
        return Typed("Input", d)
    if value is not None:
        d["Value"] = value
    if expr is not None:
        d["Expression"] = expr
    return Typed("Input", d)


class Tool(object):
    def __init__(self, name, kind, inputs=None, user_controls=None, extra=None):
        self.name, self.kind = name, kind
        self.inputs = OrderedDict(inputs or {})
        self.user_controls = user_controls
        self.extra = extra or {}

    def set(self, key, value=None, expr=None):
        self.inputs[key] = inp(value, expr)
        return self

    def link(self, key, src, out="Output"):
        self.inputs[key] = inp(src=src, out=out)
        return self

    def lua_body(self):
        d = OrderedDict()
        d["CtrlWZoom"] = False
        d["Inputs"] = self.inputs
        if self.user_controls:
            d["UserControls"] = Typed("", Ordered(self.user_controls)) if False else Raw("ordered() " + lua(OrderedDict(self.user_controls), 4))
        for k, v in self.extra.items():
            d[k] = v
        return Typed(self.kind, d)


# ───────────── 노드 ─────────────
def rect(name, cx, cy, w, h, cr=0.0):
    t = Tool(name, "RectangleMask")
    t.set("MaskWidth", 1920).set("MaskHeight", 1080).set("PixelAspect", [1, 1])
    t.set("ClippingMode", fuid("None"))
    t.set("Center", [cx, cy]).set("Width", w).set("Height", h).set("CornerRadius", cr)
    return t


def ellipse(name, cx, cy, w, h):
    t = Tool(name, "EllipseMask")
    t.set("MaskWidth", 1920).set("MaskHeight", 1080).set("PixelAspect", [1, 1])
    t.set("ClippingMode", fuid("None"))
    t.set("Center", [cx, cy]).set("Width", w).set("Height", h)
    return t


def solid(name, rgb, mask=None, alpha=1.0):
    t = Tool(name, "Background")
    t.set("Width", 1920).set("Height", 1080).set("UseFrameFormatSettings", 1)
    t.set("TopLeftRed", rgb[0]).set("TopLeftGreen", rgb[1]).set("TopLeftBlue", rgb[2]).set("TopLeftAlpha", alpha)
    if mask:
        t.link("EffectMask", mask, "Mask")
    return t


def gradient_v(name, top, bottom):
    t = Tool(name, "Background")
    t.set("Width", 1920).set("Height", 1080).set("UseFrameFormatSettings", 1)
    t.set("Type", fuid("Vertical"))
    for c, (r, g, b) in (("TopLeft", top), ("TopRight", top), ("BottomLeft", bottom), ("BottomRight", bottom)):
        t.set(c + "Red", r).set(c + "Green", g).set(c + "Blue", b).set(c + "Alpha", 1)
    return t


def text(name, s, font, style, size, cx, cy, rgb, align=0, mask=None, spacing=None):
    t = Tool(name, "TextPlus")
    t.set("Width", 1920).set("Height", 1080).set("UseFrameFormatSettings", 1)
    t.set("Center", [cx, cy])
    t.set("StyledText", s).set("Font", font).set("Style", style).set("Size", size)
    t.set("Red1", rgb[0]).set("Green1", rgb[1]).set("Blue1", rgb[2]).set("Alpha1", 1)
    t.set("HorizontalLeftCenterRight", align).set("VerticalTopCenterBottom", 0)
    t.set("Enabled3", 0).set("Enabled4", 0)
    if spacing is not None:
        t.set("CharacterSpacing", spacing)
    if mask:
        t.link("EffectMask", mask, "Mask")
    return t


def merge(name, bg, fg, blend=None, blend_expr=None, center=None, size_expr=None):
    t = Tool(name, "Merge")
    t.link("Background", bg).link("Foreground", fg)
    t.set("PerformDepthMerge", 0)
    if blend is not None or blend_expr is not None:
        t.set("Blend", blend if blend is not None else 1, blend_expr)
    if isinstance(center, str):                 # 표현식: 앞 그림을 옮긴다((0.5, 0.5) = 제자리)
        t.set("Center", [0.5, 0.5], center)
    elif center is not None:
        t.set("Center", list(center))
    if size_expr:                               # 앞 그림 배율(Merge 는 앞 그림을 자기 틀에 가두지 않아 키워도 안 잘린다)
        t.set("Size", 1, size_expr)
    return t


def canvas(name):
    """투명 1920x1080 — 여러 층을 쌓을 바탕."""
    t = Tool(name, "Background")
    t.set("Width", 1920).set("Height", 1080).set("UseFrameFormatSettings", 1)
    t.set("TopLeftRed", 0).set("TopLeftGreen", 0).set("TopLeftBlue", 0).set("TopLeftAlpha", 0)
    return t


def loader(name, path=""):
    t = Tool(name, "Loader")
    t.inputs["Clip"] = Typed("Input", OrderedDict([("Value", Typed("Clip", OrderedDict([("ID", "Clip1"), ("Filename", path), ("FormatID", "PNGFormat"), ("Loop", True), ("StartFrame", -1), ("LengthSetManually", True), ("TrimIn", 0), ("TrimOut", 0), ("ExtendFirst", 0), ("ExtendLast", 0), ("GlobalStart", -2000000000), ("GlobalEnd", 2000000000)])))]))
    t.set("Loop", 1)
    return t


def spline(name, keys, linear=True):
    """BezierSpline 키프레임 {프레임: 값}."""
    kf = OrderedDict()
    for f in sorted(keys):
        kf[Raw("[%s]" % _num(f))] = Raw("{ %s%s }" % (_num(keys[f]), ", Flags = { Linear = true }" if linear else ""))
    t = Tool(name, "BezierSpline")
    t.extra["KeyFrames"] = kf
    return t


# ───────────── 매크로 ─────────────
class Macro(object):
    def __init__(self, name):
        self.name = name
        self.tools = OrderedDict()
        self.published = []            # (key, dict)
        self.output = None

    def add(self, *tools):
        for t in tools:
            self.tools[t.name] = t
        return tools[-1] if tools else None

    def publish(self, tool, source, name=None, default=None, group=None, page=None, key=None):
        d = OrderedDict([("SourceOp", tool), ("Source", source)])
        if name:
            d["Name"] = name
        if group is not None:
            d["ControlGroup"] = group
        if default is not None:
            d["Default"] = default
        if page:
            d["Page"] = page
        self.published.append((key or "Input%d" % (len(self.published) + 1), d))

    def publish_color(self, tool, name, group, rgb, prefix="TopLeft"):
        for i, ch in enumerate(("Red", "Green", "Blue")):
            self.publish(tool, prefix + ch, name=name if i == 0 else None, group=group, default=rgb[i])

    def to_setting(self):
        body = OrderedDict()
        ins = OrderedDict((k, Typed("InstanceInput", d)) for k, d in self.published)
        body["Inputs"] = Raw("ordered() " + lua(ins, 3))
        body["Outputs"] = {"MainOutput1": Typed("InstanceOutput", OrderedDict([("SourceOp", self.output), ("Source", "Output")]))}
        body["ViewInfo"] = Raw("GroupInfo { Pos = { 0, 0 } }")
        tools = OrderedDict((n, t.lua_body()) for n, t in self.tools.items())
        body["Tools"] = Raw("ordered() " + lua(tools, 3))
        top = OrderedDict()
        top["Tools"] = Raw("ordered() " + lua({self.name: Typed("MacroOperator", body)}, 1))
        top["ActiveTool"] = self.name
        return lua(top, 0) + "\n"


def user_number(name, default, lo=0, hi=60, integer=True, page="Controls"):
    d = OrderedDict([("LINKS_Name", name), ("LINKID_DataType", "Number"), ("INPID_InputControl", "SliderControl"),
                     ("INP_Default", default), ("INP_MinScale", lo), ("INP_MaxScale", hi), ("INP_Integer", integer), ("ICS_ControlPage", page)])
    return d
