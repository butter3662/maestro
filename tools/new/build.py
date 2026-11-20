# 새 곡 데이터 생성 (Mutopia LilyPond 소스를 데이터로만 읽음)
import sys, json, re, math
sys.path.insert(0, '/home/claude/tools')
import lyparse
F = '/home/claude/mutopiaproject/mutopiaproject/ftp/'
N='C C# D D# E F F# G G# A A# B'.split()
def nm(m):return N[m%12]+str(m//12-1)

def seq(segs, Q):
    """segs: [(file, var, lang, shift)] 를 차례로 이어 붙임. 각 구간 길이는 마디 배수로 올림"""
    out = []; off = 0
    for f, var, lang, sh in segs:
        ev = lyparse.parse(F + f, var, lang)
        L = max(t + d for t, d, p in ev) + sh
        for t, d, p in ev: out.append((off + t + sh, d, p))
        off += math.ceil(L / Q - 1e-6) * Q
    return out

def clair(which):
    """드뷔시 달빛: \\parallelMusic(마디를 4성부가 번갈아 적는 형식)의 첫 구간(달빛 주제)만 읽음"""
    src = lyparse.strip_comments(open(F + 'DebussyC/L75/debussy_Ste_Bergamesq_Clair/debussy_Ste_Bergamesq_Clair.ly').read())
    names = ['rhUpRed', 'rhDownGreen', 'lhUpBlue', 'lhDownGrey']; who = {'rhUp': 0, 'rhDown': 1, 'lhUp': 2, 'lhDown': 3}[which]
    a = src.index('\\parallelMusic'); b = src.index('{', a)
    d = 0; k = b
    while True:
        if src[k] == '{': d += 1
        elif src[k] == '}':
            d -= 1
            if d == 0: break
        k += 1
    body = src[b + 1:k]
    chunks = []; cur = ''; dd = 0
    for ch in body:
        if ch == '{': dd += 1
        if ch == '}': dd -= 1
        if ch == '|' and dd == 0: chunks.append(cur); cur = ''
        else: cur += ch
    if cur.strip(): chunks.append(cur)
    mine = [c for i2, c in enumerate(chunks) if i2 % 4 == who]
    rel = re.search(r'(?m)^' + which + r'\s*=\s*\\relative\s+(\S+)', src).group(1)
    text = which + ' = \\relative ' + rel + ' {' + ' | '.join(mine) + '}'
    open('/tmp/clair_' + which + '.ly', 'w').write(text)
    return lyparse.parse('/tmp/clair_' + which + '.ly', which, 'english')

def flat(ev, start_q, end_q, shift=0):
    r = []
    for t, d, p in ev:
        t2 = t + shift
        if t2 < start_q - 1e-9 or t2 >= end_q - 1e-9: continue
        if not (21 <= p <= 108): continue
        d = min(d, end_q - t2)
        r += [round((t2 - start_q) * 96), max(1, round(d * 96)), p]
    return r

SONGS = []
def add(sid, title, comp, meter, beatSym, kw, Q, qb, key, tp, dyn, boss, parts, bars, src, mapping=None, extra=None):
    nb = bars
    d = dict(id=sid, title=title, composer=comp, meterTxt=meter, beatSym=beatSym, kw=kw, qPerBar=Q, qPerBeat=qb,
             key=key, boss=boss, nBars=nb, tp=tp, dyn=dyn, parts=parts, src=src)
    if mapping: d['map'] = mapping
    if extra: d.update(extra)
    # 검증: 첫 4마디 선율
    top = {}
    for k, v in parts.items():
        for i in range(0, len(v), 3):
            t = v[i] / 96
            if t < Q * 4: top[t] = max(top.get(t, 0), v[i + 2])
    print(sid, {k: len(v) // 3 for k, v in parts.items()}, nb, 'bars |', ' '.join(nm(top[t]) for t in sorted(top))[:160], file=sys.stderr)
    SONGS.append(d)

L = 'english'; NL = 'nederlands'
# 1 베토벤 운명 1악장 (피아노 편곡) 2/4, 2분음표 = 108
f = 'BeethovenLv/O67/beethoven_fifth_op67/beethoven_fifth_op67-lys/mvt01-allegroconbrio.ly'
nb = 94; Q = 2
add('fate', '운명 교향곡 1악장', 'L. v. 베토벤', '2/4', '♩', 'symphony 5 fate beethoven 운명 교향곡 5번', Q, 1, 0, 216, 'f', False,
    {'rh': flat(lyparse.parse(F + f, 'partRH', L), 0, nb * Q), 'lh': flat(lyparse.parse(F + f, 'partLH', L), 0, nb * Q)}, nb,
    'Mutopia Project')
# 2 비창 3악장 2/2 (못갖춘마디 1.5박 → 앞에 쉼 2.5박 붙여 한 마디로)
f = 'BeethovenLv/O13/pathetique-3/pathetique-3.ly'; Q = 4; nb = 34; sh = 2.5
add('pathetique3', '비창 소나타 3악장', 'L. v. 베토벤', '2/2', '♩', 'pathetique sonata 3rd movement rondo beethoven 비창 3악장', Q, 1, 0, 200, 'mf', False,
    {'rh': flat(lyparse.parse(F + f, 'top', NL), 0, nb * Q, sh), 'lh': flat(lyparse.parse(F + f, 'bottom', NL), 0, nb * Q, sh)}, nb, 'Mutopia Project')
# 3 브람스 자장가 3/4 (노래 선율 + 피아노)
f = 'BrahmsJ/O49/Wiegenlied/Wiegenlied-lys/Wiegenlied.ly'; Q = 3; nb = 18
mel = lyparse.parse(F + f, 'melody', NL); up = lyparse.parse(F + f, 'upper', NL); lo = lyparse.parse(F + f, 'lower', NL)
add('lullaby', '자장가 Op.49 No.4', 'J. 브람스', '3/4', '♩', 'lullaby wiegenlied brahms 자장가 브람스', Q, 1, 3, 76, 'p', False,
    {'v': flat(mel, 0, nb * Q), 'up': flat(up, 0, nb * Q), 'lo': flat(lo, 0, nb * Q)}, nb, 'Mutopia Project',
    mapping={'mel': [['v', 0]], 'har': [['up', 0, 'beat']], 'bass': [['lo', 0]], 'cb': [['lo', -12, 'low']], 'pno': [['up', 0], ['lo', 0]],
             'fl': [['v', 12]], 'tpt': [['v', 0, 'beat']], 'timp': []})
# 4 강아지 왈츠 3/4 (1마디 = 1박)
d = 'ChopinFF/O64/chopin_valse_op64_no1/chopin_valse_op64_no1-lys/'; Q = 3
rh = seq([(d + 'sec1.ly', 'secOneRHnotes', L, 0), (d + 'sec2.ly', 'secTwoRHnotes', L, 0)], Q)
lh = seq([(d + 'sec1.ly', 'secOneLHnotes', L, 0), (d + 'sec2.ly', 'secTwoLHnotes', L, 0)], Q)
nb = 36
add('minute', '강아지 왈츠 Op.64 No.1', 'F. 쇼팽', '3/4', '♩', 'minute waltz valse chopin op 64 강아지 왈츠 쇼팽', Q, 1, 1, 200, 'mf', False,
    {'rh': flat(rh, 0, nb * Q), 'lh': flat(lh, 0, nb * Q)}, nb, 'Mutopia Project')
# 5 즉흥환상곡 (4/4, 2분음표=84) 1~40마디
f = 'ChopinFF/O66/chopin_fantaisie-impromptu/chopin_fantaisie-impromptu.ly'; Q = 4; nb = 40
add('fantaisie', '즉흥환상곡 Op.66', 'F. 쇼팽', '4/4', '♩', 'fantaisie impromptu chopin op 66 즉흥환상곡 쇼팽', Q, 1, 1, 168, 'f', True,
    {'rh': flat(lyparse.parse(F + f, 'upper', NL), 0, nb * Q), 'lh': flat(lyparse.parse(F + f, 'lower', NL), 0, nb * Q)}, nb, 'Mutopia Project')
# 6 파가니니 카프리스 24번 (주제 + 1·2변주, 바이올린 독주 → 파트 배정)
f = 'PaganiniN/O1/Caprice_24/Caprice_24.ly'; Q = 2
line = seq([(f, 'music', L, 0), (f, 'varI', L, 0), (f, 'varII', L, 0)], Q); nb = 36
add('caprice24', '카프리스 24번', 'N. 파가니니', '2/4', '♩', 'caprice 24 paganini violin 카프리스 파가니니', Q, 1, 9, 112, 'f', True,
    {'v': flat(line, 0, nb * Q)}, nb, 'Mutopia Project',
    mapping={'mel': [['v', 0]], 'har': [['v', -12, 'beat']], 'bass': [['v', -12, 'low']], 'cb': [['v', -24, 'low']], 'pno': [['v', 0], ['v', -12, 'low']],
             'fl': [['v', 12]], 'tpt': [['v', 0, 'beat']], 'timp': []})
# 7 결혼 행진곡 4/4
f = 'Mendelssohn-BartholdyF/O61/Sommernachtstraum-wedding-march/Sommernachtstraum-wedding-march.ly'; Q = 4; nb = 26
add('wedding', '결혼 행진곡', 'F. 멘델스존', '4/4', '♩', 'wedding march mendelssohn midsummer night 결혼 행진곡 한여름밤의 꿈', Q, 1, 0, 116, 'f', False,
    {'rh': flat(lyparse.parse(F + f, 'rh', NL), 0, nb * Q), 'lh': flat(lyparse.parse(F + f, 'lh', NL), 0, nb * Q)}, nb, 'Mutopia Project')
# 8 카르멘 전주곡 2/4
f = 'BizetG/prelude/prelude.ly'; Q = 2; nb = 56
add('carmen', '카르멘 전주곡', 'G. 비제', '2/4', '♩', 'carmen prelude bizet overture 카르멘 서곡 투우사', Q, 1, 9, 116, 'f', False,
    {'rh': flat(lyparse.parse(F + f, 'upper', NL), 0, nb * Q), 'lh': flat(lyparse.parse(F + f, 'lower', NL), 0, nb * Q)}, nb, 'Mutopia Project')
# 9 송어 2/4 (노래 + 피아노)
d = 'SchubertF/D550/forelle/forelle-lys/'; Q = 2; nb = 26
mel = lyparse.parse(F + d + 'melody.ly', 'melody', NL); up = lyparse.parse(F + d + 'piano.ly', 'upper', NL); lo = lyparse.parse(F + d + 'piano.ly', 'lower', NL)
add('trout', '송어', 'F. 슈베르트', '2/4', '♩', 'trout forelle schubert 송어 슈베르트', Q, 1, 1, 80, 'mf', False,
    {'v': flat(mel, 0, nb * Q), 'up': flat(up, 0, nb * Q), 'lo': flat(lo, 0, nb * Q)}, nb, 'Mutopia Project',
    mapping={'mel': [['v', 0]], 'har': [['up', 0, 'beat']], 'bass': [['lo', 0]], 'cb': [['lo', -12, 'low']], 'pno': [['up', 0], ['lo', 0]],
             'fl': [['v', 12]], 'tpt': [['v', 0, 'beat']], 'timp': []})
# 9-2 마왕 4/4 (노래 + 피아노), 1~32마디
f = 'SchubertF/D328/Erlkoenig/Erlkoenig.ly'; Q = 4; nb = 32
mel = lyparse.parse(F + f, 'meloNote', 'italiano'); up = lyparse.parse(F + f, 'pianoHautNote', 'italiano'); lo = lyparse.parse(F + f, 'pianoBasNotePart', 'italiano')
add('erlkonig', '마왕', 'F. 슈베르트', '4/4', '♩', 'erlkonig erlkoenig erlking schubert 마왕 슈베르트', Q, 1, 7, 152, 'f', False,
    {'v': flat(mel, 0, nb * Q), 'up': flat(up, 0, nb * Q), 'lo': flat(lo, 0, nb * Q)}, nb, 'Mutopia Project',
    mapping={'mel': [['v', 0]], 'har': [['up', 0, 'beat']], 'bass': [['lo', 0]], 'cb': [['lo', -12, 'low']], 'pno': [['up', 0], ['lo', 0]],
             'fl': [['v', 12]], 'tpt': [['lo', 12, 'beat']], 'timp': []})
# 10 작은 별 변주곡 (기타 2중주 편곡: 주제 + 1변주)
f = 'MozartWA/KV265/guitar-duo-complete/guitar-duo-complete-lys/guitar-duo-complete.ly'; Q = 2
a = seq([(f, 'themaA', NL, 0), (f, 'varIA', NL, 0)], Q); c = seq([(f, 'themaC', NL, 0), (f, 'varIC', NL, 0)], Q); nb = 40
add('twinkle', '작은 별 변주곡', 'W. A. 모차르트', '2/4', '♩', 'twinkle twinkle little star ah vous dirai je maman mozart 작은 별', Q, 1, 0, 100, 'mf', False,
    {'rh': flat(a, 0, nb * Q), 'lh': flat(c, 0, nb * Q)}, nb, 'Mutopia Project')
# 11 달빛 9/8 (첫 구간)
Q = 4.5
rh = clair('rhUp') + clair('rhDown'); lh = clair('lhUp') + clair('lhDown')
for w in ('rhUp','rhDown','lhUp','lhDown'): print(w, max(t+d for t,d,p in clair(w)), file=sys.stderr)
L1 = max(t + d for t, d, p in rh + lh); nb = math.ceil(L1 / Q - 1e-6)
add('clair', '달빛', 'C. 드뷔시', '9/8', '♩.', 'clair de lune debussy suite bergamasque 달빛 드뷔시', Q, 1.5, 1, 36, 'p', False,
    {'rh': flat(rh, 0, nb * Q), 'lh': flat(lh, 0, nb * Q)}, nb, 'Mutopia Project')
json.dump(SONGS, open('/tmp/new_mutopia.json', 'w'), ensure_ascii=False, separators=(',', ':'))
