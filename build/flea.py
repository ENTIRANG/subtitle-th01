# -*- coding: utf-8 -*-
"""원본 컴포지션(리졸브가 내보낸 .comp)을 Fusion 매크로로 감싼다. 원본 노드의 값은 바꾸지 않는다.

하는 것: MediaOut(Saver) 제거, 원본 클립 길이에 묶인 GlobalIn/GlobalOut 제거, 편집 페이지에서 고칠 글자 입력 열기,
출력 뒤에 위치·크기 Transform(th_xf) 추가. 색 관리 없는 프로젝트용(yrgb)은 색 입력 값에 BT.709 OETF 를 적용한다.
source/comps 의 크레딧은 원본 파일에서 실명을 OOO 로 바꿔 실었다."""
import os, re
from collections import OrderedDict
from elements import oetf

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "source", "comps")
COLOR_INPUT = re.compile(r"^(\s*)(\w*(?:Red|Green|Blue)\d*) = Input \{ Value = ([-\d.e]+), \},?$")
GLOBAL_RANGE = re.compile(r"\bGlobal(In|Out) = Input \{ Value = [-\d.]+, \},?$")
STYLED_TEXT = re.compile(r'^(\s*)StyledText = Input \{ Value = "(.*)", \},?$')


def tool_blocks(path):
    lines = open(path, encoding="utf-8").read().replace("\r", "").split("\n")
    i = next(k for k, l in enumerate(lines) if l == "\tTools = {" or l == "\tTools = ordered() {")
    blocks, cur, name, kind = OrderedDict(), None, None, None
    for l in lines[i + 1:]:
        if l.startswith("\t}"):
            break
        m = re.match(r"^\t\t(\[?\"?[^\s=\"\]]+\"?\]?) = (\w+) \{$", l)
        if m and cur is None:
            name, kind, cur = m.group(1).strip('[]"'), m.group(2), [l]
            continue
        if cur is not None:
            cur.append(l)
            if l.startswith("\t\t}"):
                blocks[name] = (kind, cur)
                cur = None
    return blocks


def lua_str(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class WrappedMacro(object):
    def __init__(self, name, comp, publish, texts=None):
        self.name = name
        self.blocks = tool_blocks(os.path.join(SRC, comp))
        kind, body = self.blocks.pop("MediaOut1")
        self.output = re.search(r'SourceOp = "([^"]+)"', "\n".join(body)).group(1)
        self.publish = publish
        self.texts = texts or {}

    def to_setting(self, pipe="cm"):
        ins = list(self.publish) + [("th_xf", "Center", "위치"), ("th_xf", "Size", "크기")]
        out = ["{", "\tTools = ordered() {", "\t\t%s = MacroOperator {" % self.name, "\t\t\tInputs = ordered() {"]
        for i, (tool, src, label) in enumerate(ins, 1):
            out += ["\t\t\t\tInput%d = InstanceInput {" % i, '\t\t\t\t\tSourceOp = "%s",' % tool, '\t\t\t\t\tSource = "%s",' % src,
                    '\t\t\t\t\tName = "%s",' % label]
            if src == "Center":
                out.append('\t\t\t\t\tPage = "Controls",')
            if src == "Size":
                out.append("\t\t\t\t\tDefault = 1,")
            out.append("\t\t\t\t},")
        out += ["\t\t\t},", "\t\t\tOutputs = {", "\t\t\t\tMainOutput1 = InstanceOutput {", '\t\t\t\t\tSourceOp = "th_xf",',
                '\t\t\t\t\tSource = "Output",', "\t\t\t\t}", "\t\t\t},", "\t\t\tViewInfo = GroupInfo { Pos = { 0, 0 } },", "\t\t\tTools = ordered() {"]
        for name, (kind, body) in self.blocks.items():
            body = list(body)
            if body[-1].rstrip() == "\t\t}":           # 원본의 마지막 도구는 쉼표 없이 끝난다 — 뒤에 th_xf 를 붙이므로 쉼표를 단다
                body[-1] = body[-1].rstrip() + ","
            for l in body:
                if GLOBAL_RANGE.search(l.strip()):
                    continue
                m = STYLED_TEXT.match(l)
                if m and name in self.texts:
                    l = '%sStyledText = Input { Value = "%s", },' % (m.group(1), lua_str(self.texts[name]))
                c = COLOR_INPUT.match(l)
                if c and pipe == "yrgb":
                    l = "%s%s = Input { Value = %r, }," % (c.group(1), c.group(2), oetf(float(c.group(3))))
                out.append("\t\t" + l)
        out += ["\t\t\t\tth_xf = Transform {", "\t\t\t\t\tInputs = {",
                '\t\t\t\t\t\tInput = Input { SourceOp = "%s", Source = "Output", },' % self.output, "\t\t\t\t\t},", "\t\t\t\t},"]
        out += ["\t\t\t},", "\t\t}", "\t},", '\tActiveTool = "%s"' % self.name, "}", ""]
        return "\n".join(out)


def opening():
    return WrappedMacro("th01_Opening", "flea_V3_58.comp",
                        [("Text1", "StyledText", "제목"), ("Text2", "StyledText", "부제")])


def section():
    return WrappedMacro("th01_Section", "flea_V3_209.comp",
                        [("Text3", "StyledText", "제목"), ("Text1", "StyledText", "아이콘"), ("Text4", "StyledText", "라벨"),
                         ("Text5", "StyledText", "부제"), ("Text2", "StyledText", "배경 글자")])


def credits():
    return WrappedMacro("th01_Credits", "flea_V3_2862.comp",
                        [("Text1", "StyledText", "큰 줄"), ("Text2", "StyledText", "역할"), ("Text3", "StyledText", "고지")])


def watermark():
    return WrappedMacro("th01_Watermark", "flea_V6_0.comp", [("Text1", "StyledText", "글자")])


ELEMENTS = [
    ("th01 오프닝 타이틀", opening, 151),
    ("th01 섹션 타이틀", section, 184),
    ("th01 크레딧", credits, 114),
    ("th01 워터마크", watermark, 150),
]
