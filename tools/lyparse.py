"""LilyPond 부분 파서 (데이터로만 읽음, 실행하지 않음).
지원: \\relative, 음표/화음/쉼표/공백(s), 길이·점, 붙임줄 ~, q, \\times / \\tuplet, \\grace류 건너뜀,
<< a \\\\ b >> 에서 첫 성부만, \\repeat volta(한 번) + \\alternative(마지막), 나머지 \\명령·#스킴은 무시.
출력: [(시작(4분음표 단위), 길이, [midi...])]
"""
import re, sys, json
from fractions import Fraction as Fr

STEP = {'c': 0, 'd': 1, 'e': 2, 'f': 3, 'g': 4, 'a': 5, 'b': 6}
SEMI = [0, 2, 4, 5, 7, 9, 11]


def pitch_name(tok, lang):
    """음 이름 → (음이름 인덱스 0~6, 변화표 반음수). 아니면 None"""
    t = tok
    if lang == 'deutsch':
        if t == 'h': return 6, 0
        if t == 'b': return 6, -1
        if t == 'his': return 6, 1
        if t == 'heses': return 6, -2
        if t == 'hisis': return 6, 2
        if t == 'es': return 2, -1
        if t == 'eses': return 2, -2
        if t == 'as': return 5, -1
        if t == 'asas': return 5, -2
        base = t[0]
        if base not in 'cdefga': return None
        rest = t[1:]
    else:  # nederlands
        if t in ('es', 'ees'): return 2, -1
        if t in ('eses', 'eeses'): return 2, -2
        if t in ('as', 'aes'): return 5, -1
        if t in ('asas', 'aeses'): return 5, -2
        base = t[0]
        if base not in 'cdefgab': return None
        rest = t[1:]
    acc = 0
    while rest:
        if rest.startswith('is'): acc += 1; rest = rest[2:]
        elif rest.startswith('es'): acc -= 1; rest = rest[2:]
        elif rest.startswith('s') and base in 'ea' and acc == 0 and lang == 'deutsch': acc -= 1; rest = rest[1:]
        else: return None
    return STEP[base], acc


def strip_comments(s):
    s = re.sub(r'%\{.*?%\}', ' ', s, flags=re.S)
    out = []
    for line in s.split('\n'):
        # 문자열 안의 % 는 드묾 — 단순 처리
        i = line.find('%')
        out.append(line if i < 0 else line[:i])
    return '\n'.join(out)


TOKRE = re.compile(r'''
 (?P<str>"(?:[^"\\]|\\.)*")
|(?P<art>[-^_](?:[>.^+!_|-]|[0-9]+|"(?:[^"\\]|\\.)*"))
|(?P<dyn>\\[<>!()\[\]~])
|(?P<scheme>\#)
|(?P<dbl><<|>>|\\\\)
|(?P<cmd>\\[A-Za-z]+)
|(?P<chordo><)
|(?P<chordc>>(?P<cdur>[0-9]*\.*(?:\*[0-9/]+)?))
|(?P<note>[a-z]+[',]*[!?]?(?:=[',]*)?[0-9]*\.*(?:\*[0-9/]+)?)
|(?P<brace>[{}])
|(?P<tie>~)
|(?P<other>\S)
''', re.X)


def tokenize(s):
    toks = []
    i = 0
    n = len(s)
    while i < n:
        if s[i].isspace(): i += 1; continue
        if s[i] == '#':  # 스킴 표현식 건너뛰기 (자리표시 토큰만 남김)
            toks.append(('scheme', '#'))
            i += 1
            if i < n and s[i] == '#': i += 2; continue
            if i < n and s[i] == "'": i += 1
            if i < n and s[i] == '(':
                d = 0
                while i < n:
                    if s[i] == '(': d += 1
                    elif s[i] == ')':
                        d -= 1
                        if d == 0: i += 1; break
                    elif s[i] == '"':
                        i += 1
                        while i < n and s[i] != '"': i += 2 if s[i] == '\\' else 1
                    i += 1
                continue
            if i < n and s[i] == '{':  # #{ ... #}
                j = s.find('#}', i)
                i = n if j < 0 else j + 2
                continue
            while i < n and not s[i].isspace() and s[i] not in '{}': i += 1
            continue
        m = TOKRE.match(s, i)
        if not m: i += 1; continue
        toks.append((m.lastgroup if m.lastgroup != 'cdur' else 'chordc', m.group(0)))
        i = m.end()
    return toks


SKIP_ARGS = {'\\key': 2, '\\time': 1, '\\clef': 1, '\\partial': 1, '\\bar': 1, '\\mark': 1, '\\ottava': 0,
             '\\change': 3, '\\context': 1, '\\new': 1, '\\set': 0, '\\override': 0, '\\revert': 2,
             '\\tempo': 0, '\\markup': 0, '\\finger': 1, '\\moveFingering': 0, '\\tag': 1,
             '\\remove': 1, '\\consists': 1, '\\accidentalStyle': 1, '\\transposition': 1}


class P:
    def __init__(self, toks, lang, defs):
        self.t = toks; self.i = 0; self.lang = lang; self.defs = defs
        self.out = []; self.time = Fr(0); self.dur = Fr(1)  # 4분음표=1
        self.prev = None  # (step, octave) for relative
        self.scale = Fr(1); self.last_chord = None; self.pending_tie = {}

    def peek(self, k=0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else (None, None)

    def take(self):
        x = self.peek(); self.i += 1; return x

    def parse_dur(self, txt):
        m = re.match(r'([0-9]+)?(\.*)(?:\*([0-9]+)(?:/([0-9]+))?)?$', txt)
        if not m: return self.dur
        if m.group(1):
            base = Fr(4, int(m.group(1)))
            d = base; add = base
            for _ in m.group(2): add /= 2; d += add
            self.dur = d
        d = self.dur
        if m.group(3): d = d * int(m.group(3)) / (int(m.group(4)) if m.group(4) else 1)
        return d

    def rel_pitch(self, name, octs, absolute=False):
        st, acc = name
        up = octs.count("'") - octs.count(',')
        if self.prev is None or absolute:
            octv = 3 + up  # c = C3 (midi 48) ; c' = 60
        else:
            pst, poc = self.prev
            best = None
            for oc in (poc - 1, poc, poc + 1):
                diff = (oc * 7 + st) - (poc * 7 + pst)
                if abs(diff) <= 3:
                    best = oc; break
            if best is None: best = poc
            octv = best + up
        self.prev = (st, octv)
        return (octv + 1) * 12 + SEMI[st] + acc

    def emit(self, pitches, d, tie_next):
        dd = d * self.scale
        if pitches:
            self.out.append([float(self.time), float(dd), pitches, tie_next])
        self.time += dd

    def parse_note_tok(self, txt):
        m = re.match(r"([a-z]+)([',]*)([!?]?)(?:=([',]*))?(.*)$", txt)
        name, octs, _, _, rest = m.groups()
        return name, octs, rest

    def music(self, until=None):
        """until: '}' 또는 '>>' 까지"""
        while True:
            k, v = self.peek()
            if k is None: return
            if k == 'brace' and v == '}':
                if until == '}': self.take(); return
                self.take(); continue
            if k == 'dbl' and v == '>>':
                if until == '>>': self.take(); return
                self.take(); continue
            self.element()

    def skip_element(self):
        """다음 음악 요소 하나를 소리 없이 건너뜀(시간도 안 씀)"""
        save = (self.out, self.time, self.prev)
        self.out = []; t0 = self.time
        self.element()
        self.out = save[0]; self.time = t0

    def skip_balanced(self, open_v, close_v):
        d = 1
        while True:
            k, v = self.take()
            if k is None: return
            if v == open_v: d += 1
            elif v == close_v:
                d -= 1
                if d == 0: return

    def element(self):
        k, v = self.take()
        if k == 'brace' and v == '{':
            self.music('}'); return
        if k == 'dbl' and v == '<<':
            # 첫 성부만 연주, \\ 이후 나머지 성부는 건너뜀
            t0 = self.time; prev0 = self.prev
            while True:
                k2, v2 = self.peek()
                if k2 is None: return
                if k2 == 'dbl' and v2 == '\\\\':
                    self.take(); t1 = self.time
                    self.skip_balanced('<<', '>>'); return
                if k2 == 'dbl' and v2 == '>>':
                    self.take(); return
                self.element()
        if k == 'cmd':
            c = v
            if c == '\\relative':
                k2, v2 = self.peek()
                if k2 == 'note':
                    self.take(); name, octs, _ = self.parse_note_tok(v2)
                    pn = pitch_name(name, self.lang)
                    self.prev = None
                    if pn: self.rel_pitch(pn, octs, absolute=True)
                return
            if c in ('\\times', '\\tuplet', '\\tupletSpan'):
                k2, v2 = self.take()
                frac = v2
                # 다음 토큰이 '/' 형태로 나뉘었을 수 있음
                m = re.match(r'([0-9]+)', frac or '')
                if self.peek()[1] == '/':
                    self.take(); k3, v3 = self.take(); frac = f"{frac}/{v3}"
                try:
                    a, b = [int(x) for x in re.findall(r'[0-9]+', frac)[:2]]
                except Exception:
                    a, b = 2, 3
                f = Fr(a, b) if c == '\\times' else Fr(b, a)
                if self.peek()[0] == 'note' and re.match(r'^[0-9]', self.peek()[1] or ''):
                    self.take()  # \tuplet 3/2 4 { } 의 묶음 길이
                old = self.scale; self.scale = self.scale * f
                self.element(); self.scale = old; return
            if c in ('\\grace', '\\acciaccatura', '\\appoggiatura', '\\slashedGrace', '\\afterGrace'):
                self.skip_element()
                if c == '\\afterGrace': self.skip_element()
                return
            if c == '\\repeat':
                self.take(); self.take()  # volta n
                self.element()
                if self.peek()[1] == '\\alternative':
                    self.take()
                    # { {alt1} {alt2} } → 마지막만
                    k3, v3 = self.take()
                    alts_start = self.i
                    # 대안들을 모두 건너뛰며 마지막 위치 기록
                    starts = []
                    while True:
                        k4, v4 = self.peek()
                        if v4 == '}': self.take(); break
                        starts.append(self.i)
                        self.skip_element()
                    if starts:
                        end = self.i; self.i = starts[-1]; self.element(); self.i = end
                return
            if c in ('\\set', '\\override'):
                # ... = 값 까지
                while True:
                    k3, v3 = self.take()
                    if k3 is None or v3 == '=': break
                k3, v3 = self.peek()
                if k3 in ('note', 'other', 'str', 'scheme'): self.take()
                return
            if c == '\\once' or c == '\\temporary': return
            if c == '\\tempo':
                # \tempo "텍스트" 4 = 160  또는 \tempo 4 = 160
                if self.peek()[0] == 'str': self.take()
                if self.peek()[0] == 'note' and re.match(r'^[0-9]', self.peek()[1]):
                    self.take();
                    if self.peek()[1] == '=': self.take(); self.take()
                return
            if c == '\\markup':
                k3, v3 = self.peek()
                if v3 == '{': self.take(); self.skip_balanced('{', '}')
                else: self.take()
                return
            if c in SKIP_ARGS and SKIP_ARGS[c]:
                for _ in range(SKIP_ARGS[c]): self.take()
                return
            if c[1:] in self.defs:  # 사용자 정의 음악 변수
                return
            return  # 인자 없는 명령으로 간주
        if k == 'chordo':
            pitches = []; first = None
            save_prev = self.prev
            while True:
                k2, v2 = self.take()
                if k2 is None: return
                if k2 == 'chordc':
                    durtxt = v2[1:]; break
                if k2 == 'note':
                    name, octs, _ = self.parse_note_tok(v2)
                    pn = pitch_name(name, self.lang)
                    if pn:
                        p = self.rel_pitch(pn, octs)
                        if first is None: first = self.prev
                        pitches.append(p)
            if first: self.prev = first
            d = self.parse_dur(re.sub(r'[^0-9.*/]', '', durtxt))
            self.last_chord = pitches
            self.emit(pitches, d, self.after_tie())
            return
        if k == 'note':
            name, octs, rest = self.parse_note_tok(v)
            durtxt = re.sub(r'[^0-9.*/]', '', rest)
            if name in ('r', 's', 'R'):
                d = self.parse_dur(durtxt); self.emit([], d, False); return
            if name == 'q':
                d = self.parse_dur(durtxt); self.emit(list(self.last_chord or []), d, self.after_tie()); return
            pn = pitch_name(name, self.lang)
            if not pn:
                return
            p = self.rel_pitch(pn, octs)
            d = self.parse_dur(durtxt)
            self.emit([p], d, self.after_tie())
            return
        # 기타 기호는 무시
        return

    def after_tie(self):
        if self.peek()[0] == 'tie':
            self.take(); return True
        return False


def find_var(src, name):
    m = re.search(r'(?m)^' + re.escape(name) + r'\s*=', src)
    if not m: raise SystemExit('no var ' + name)
    i = m.end()
    # 첫 { 를 찾고 균형 맞춰 끝까지
    j = src.index('{', i)
    head = src[i:j]
    d = 0; k = j
    while k < len(src):
        if src[k] == '{': d += 1
        elif src[k] == '}':
            d -= 1
            if d == 0: break
        k += 1
    return head + src[j:k + 1]


def merge_ties(ev):
    out = []
    pend = {}
    for t, d, ps, tie in ev:
        keep = []
        for p in ps:
            if p in pend:
                e = pend.pop(p); e[1] = t + d - e[0]
                if tie: pend[p] = e
            else:
                e = [t, d, p]; out.append(e)
                if tie: pend[p] = e
        # 붙임줄 이어지지 않은 대기 음 정리
        for p in list(pend):
            if p not in ps and pend[p][0] + pend[p][1] < t - 1e-9: pend.pop(p)
    return out


def parse(path, var, lang):
    src = strip_comments(open(path, encoding='utf-8', errors='replace').read())
    defs = set(re.findall(r'(?m)^([A-Za-z]+)\s*=', src))
    body = find_var(src, var)
    toks = tokenize(body)
    p = P(toks, lang, defs)
    while p.i < len(p.t): p.element()
    return merge_ties(p.out)


if __name__ == '__main__':
    path, var, lang = sys.argv[1:4]
    ev = parse(path, var, lang)
    json.dump(ev, sys.stdout)
