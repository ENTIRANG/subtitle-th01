# -*- coding: utf-8 -*-
"""templates/*.setting 검사 — 문법과 의존 순환. 둘 다 리졸브에서 조용히 망가진다.

문법: 리졸브는 문법이 틀린 .setting 을 말없이 빈 컴포지션으로 넣는다. 괄호 짝과 항목 사이 쉼표를 본다.
순환: 순환이 있으면 Fusion 이 프레임을 끝내지 못하고 리졸브가 멈춘다.
  노드 두 종류: render(T) = T 의 그림, value(T) = T 의 입력값(표현식 포함).
  render(T) ← value(T), render(연결된 입력의 SourceOp)
  value(T)  ← 표현식이 X.Output 을 읽으면 render(X), X.입력 을 읽으면 value(X)(자기 자신 제외),
              self.Output 이면 render(T), 연결(SourceOp)로 들어오는 입력(스플라인 같은 모디파이어 포함)은 render(SourceOp)

    python build/check_cycles.py        # 문제가 있으면 종료코드 1
"""
import os, re, sys, glob

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
KEY = r"\[?\"?[\wㄱ-힣]+\"?\]?"
TOOL = re.compile(r"\n\t{3,4}(" + KEY + r") = (\w+) \{")
SOURCE_OP = re.compile(r'SourceOp = "([^"]+)"')
EXPRESSION = re.compile(r'Expression = "((?:[^"\\]|\\.)*)"')
STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
REF = re.compile(r"\b([A-Za-z_]\w*)\.(\w+)")
SELF_REF = re.compile(r"\bself\.(\w+)")
MISSING_COMMA = re.compile(r"\}[ \t]*\n[ \t]*(" + KEY + r")[ \t]*=")


def syntax_errors(path):
    s = open(path, encoding="utf-8").read()
    body = STRING.sub('""', s)                      # 문자열 안의 괄호는 빼고 센다
    errs = []
    if body.count("{") != body.count("}"):
        errs.append("괄호 짝이 안 맞는다: { %d, } %d" % (body.count("{"), body.count("}")))
    for m in MISSING_COMMA.finditer(body):
        errs.append("쉼표 없음: %s 앞" % m.group(1))
    return errs


def parse(path):
    s = open(path, encoding="utf-8").read()
    i = s.index("Tools = ordered() {", s.index("MacroOperator"))
    body = s[i:]
    tools = {}
    for m in TOOL.finditer(body):
        tools.setdefault(m.group(1).strip('[]"'), m.start())
    names = sorted(tools, key=lambda k: tools[k])
    spans = {}
    for a, b in zip(names, names[1:] + [None]):
        spans[a] = body[tools[a]: tools[b] if b else len(body)]
    return spans


def graph(spans):
    names = set(spans)
    g = {}
    for t, txt in spans.items():
        rv = g.setdefault(("render", t), set())
        rv.add(("value", t))
        vv = g.setdefault(("value", t), set())
        for src in SOURCE_OP.findall(txt):
            if src in names and src != t:
                rv.add(("render", src))
                vv.add(("render", src))
        for ex in EXPRESSION.findall(txt):
            for x, rest in REF.findall(ex):
                if x not in names:
                    continue
                if rest == "Output":
                    vv.add(("render", x))
                elif x != t:
                    vv.add(("value", x))
            for rest in SELF_REF.findall(ex):
                if rest == "Output":
                    vv.add(("render", t))
    return g


def cycles(g):
    seen, stack, on, out = set(), [], set(), []

    def dfs(v):
        seen.add(v); stack.append(v); on.add(v)
        for w in g.get(v, ()):
            if w not in seen:
                dfs(w)
            elif w in on:
                out.append(stack[stack.index(w):] + [w])
        stack.pop(); on.discard(v)

    sys.setrecursionlimit(10000)
    for v in list(g):
        if v not in seen:
            dfs(v)
    return out


def main():
    bad = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "templates", "*.setting"))):
        name = os.path.basename(p)
        se = syntax_errors(p)
        cs = cycles(graph(parse(p)))
        if se:
            print("SYNTAX", name, "; ".join(se[:3]))
        if cs:
            print("CYCLE ", name, " -> ".join("%s(%s)" % (k[1], k[0]) for k in cs[0]))
        if se or cs:
            bad += 1
        else:
            print("ok    ", name)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
