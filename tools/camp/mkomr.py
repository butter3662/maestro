import json, sys
N='C C# D D# E F F# G G# A A# B'.split()
def nm(m):return N[m%12]+str(m//12-1)
def parts(path, BAR, nb, fixfn=None, start=1):
    M = json.load(open(path))[start-1:start-1+nb]
    rh, lh = [], []; off = 0
    for i, m in enumerate(M, start):
        for s, dst in ((0, rh), (1, lh)):
            seen = {}
            for t, d, p in m['staffs'][s]['notes']:
                if fixfn: t = fixfn(i, s, t, p)
                t = round(t); d = round(d)
                if t >= BAR or t < 0: continue
                k = (t, p)
                if k not in seen or seen[k] < d: seen[k] = min(d, BAR - t)
            for (t, p), d in sorted(seen.items()): dst += [off + t, d, p]
        off += BAR
    return {'rh': rh, 'lh': lh}
S = []
def add(**k):
    top = {}
    for v in k['parts'].values():
        for i in range(0, len(v), 3):
            if v[i] < k['qPerBar'] * 96 * 3: top[v[i]] = max(top.get(v[i], 0), v[i + 2])
    print(k['id'], {a: len(b)//3 for a, b in k['parts'].items()}, ' '.join(nm(top[t]) for t in sorted(top))[:150], file=sys.stderr)
    S.append(k)
add(id='bumblebee', title='왕벌의 비행', composer='N. 림스키코르사코프', meterTxt='2/4', beatSym='♩', kw='flight of the bumblebee rimsky korsakov 왕벌의 비행 림스키코르사코프',
    qPerBar=2, qPerBeat=1, key=9, boss=True, nBars=56, tp=172, dyn='mf', parts=parts('/tmp/bee.json', 192, 56), src='pianoclassics.net 퍼블릭 도메인 악보')
add(id='serenade', title='세레나데 (백조의 노래)', composer='F. 슈베르트 · F. 리스트 편곡', meterTxt='3/4', beatSym='♩', kw='serenade standchen staendchen schubert liszt 세레나데 슈베르트 백조의 노래',
    qPerBar=3, qPerBeat=1, key=2, boss=False, nBars=24, tp=80, dyn='p', parts=parts('/tmp/ser.json', 288, 24), src='pianoclassics.net 퍼블릭 도메인 악보')
def habfix(i, s, t, p):
    if i in (8, 16):
        if s == 0 and t == 48 and p in (58, 62): return 0
        if t >= 48: return t - 48
    return t
add(id='habanera', title='하바네라 (카르멘)', composer='G. 비제', meterTxt='2/4', beatSym='♩', kw='habanera carmen bizet 하바네라 카르멘 사랑은 길들지 않는 새',
    qPerBar=2, qPerBeat=1, key=2, boss=False, nBars=19, tp=72, dyn='mf', parts=parts('/tmp/hab.json', 192, 19, habfix), src='pianoclassics.net 퍼블릭 도메인 악보')
json.dump(S, open('/tmp/new_omr.json', 'w'), ensure_ascii=False, separators=(',', ':'))
