# 겨울바람(Knute Snortum, CC BY-SA 4.0) + 사탕요정의 춤(neonscribe 리드시트, Unlicense)
import sys, json, re, math
sys.path.insert(0, '/home/claude/tools')
import lyparse
N='C C# D D# E F F# G G# A A# B'.split()
def nm(m):return N[m%12]+str(m//12-1)
def flat(ev, s, e):
    r = []
    for t, d, p in ev:
        if t < s - 1e-9 or t >= e - 1e-9 or not (21 <= p <= 108): continue
        r += [round((t - s) * 96), max(1, round(min(d, e - t) * 96)), p]
    return r
S = []
# 겨울바람: 1~4마디 느린 서주는 빼고 5마디(Allegro con brio)부터 26마디
f = '/tmp/gh/chopin-opus-25/includes/etude-op25-no11-parts.ily'
rh = lyparse.parse(f, 'rightHand', 'english'); lh = lyparse.parse(f, 'leftHand', 'english')
Q = 4; s0 = 16; nb = 26
S.append(dict(id='winterwind', title='겨울바람 Op.25 No.11', composer='F. 쇼팽', meterTxt='4/4', beatSym='♩',
    kw='winter wind etude chopin op 25 no 11 겨울바람 에튀드 연습곡', qPerBar=Q, qPerBeat=1, key=9, boss=True, nBars=nb, tp=138, dyn='f',
    parts={'rh': flat(rh, s0, s0 + nb * Q), 'lh': flat(lh, s0, s0 + nb * Q)}))
# 사탕요정의 춤: 선율 + 화음 기호 → 화음 구성음/베이스 파트 생성
src = open('/tmp/gh/neonscribe_lilypond-lead-sheets/Core/Dance of the Sugar Plum Fairy - Ly Core - Em.ly').read()
open('/tmp/sugar.ly', 'w').write(src)
mel = lyparse.parse('/tmp/sugar.ly', 'refrainMelody', 'english')
body = re.search(r'refrainChords\s*=\s*\\chordmode\s*\{(.*?)\n\}', src, re.S).group(1)
PC = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
def pc(n):
    v = PC[n[0]]
    for suf in re.findall(r's|f', n[1:]): v += 1 if suf == 's' else -1
    return v % 12
Q2 = {'': [0, 4, 7], 'm': [0, 3, 7], 'm6': [0, 3, 7, 9], 'dim': [0, 3, 6], 'dim7': [0, 3, 6, 9], '7': [0, 4, 7, 10], '7.9-': [0, 4, 7, 10, 13], '7.5-': [0, 4, 6, 10]}
t = 0.0; ch = []; durq = 4
for tok in body.split():
    m = re.match(r'([a-g](?:s|f)?)(\d+\.?)?(?::([^/]+))?(?:/([a-g](?:s|f)?))?$', tok)
    if not m: continue
    root, dur, q, bass = m.groups()
    if dur:
        base = 4 / int(dur.rstrip('.')); durq = base * (1.5 if dur.endswith('.') else 1)
    iv = Q2.get(q or '', [0, 4, 7])
    r = pc(root); b = pc(bass) if bass else r
    ch.append((t, durq, [r + i for i in iv], b)); t += durq
# 인트로 2마디는 화음 기호 없이 반복 → 선율 시작(인트로) 뒤에 화음 맞춤
intro = 8.0   # 인트로 2마디(4/4 기준 8박)
tones, bassn = [], []
for t0, d, ivs, b in ch:
    for i in ivs: tones.append((intro + t0, d * .95, 55 + (i - 55) % 12 if True else 0))
    bassn.append((intro + t0, d * .95, 40 + (b - 40) % 12))
# 인트로: 원곡처럼 E 단조 저음 피치카토
for k in range(4): bassn.append((k * 2.0, .5, 40)); tones.append((k * 2.0 + 1, .5, 59))
L = max(tt + dd for tt, dd, pp in mel); nb2 = math.ceil(L / 4 - 1e-6)
mel_ev = [(tt, dd, pp) for tt, dd, pp in mel]
S.append(dict(id='sugarplum', title='사탕요정의 춤 (호두까기 인형)', composer='P. I. 차이콥스키', meterTxt='2/2', beatSym='♩',
    kw='dance of the sugar plum fairy nutcracker tchaikovsky 호두까기 인형 사탕요정', qPerBar=4, qPerBeat=1, key=4, boss=False, nBars=nb2, tp=144, dyn='p',
    parts={'v': flat(mel_ev, 0, nb2 * 4), 'ch': flat(tones, 0, nb2 * 4), 'bs': flat(bassn, 0, nb2 * 4)},
    map={'mel': [['v', 0]], 'har': [['ch', 0, 'low']], 'bass': [['bs', 12]], 'cb': [['bs', 0, 'beat']], 'pno': [['ch', 0], ['bs', 0]],
         'fl': [['v', 12]], 'tpt': [['ch', 12, 'beat']], 'timp': []}))
for s in S:
    top = {}
    for v in s['parts'].values():
        for i in range(0, len(v), 3):
            if v[i] < 4 * 96 * 3: top[v[i]] = max(top.get(v[i], 0), v[i + 2])
    print(s['id'], s['nBars'], {k: len(v) // 3 for k, v in s['parts'].items()}, ' '.join(nm(top[t]) for t in sorted(top))[:200], file=sys.stderr)
json.dump(S, open('/tmp/new2.json', 'w'), ensure_ascii=False, separators=(',', ':'))
