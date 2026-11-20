"""오케스트라 파트 악보(Mutopia LilyPond)를 읽어 역할별 데이터로 만든다."""
import sys, json
sys.path.insert(0, '/home/claude/tools')
from lyparse import parse
F = '/home/claude/mutopiaproject/mutopiaproject/ftp/'
H = F + 'HandelGF/hallelujah/hallelujah-lys/'
A = F + 'BachJS/BWV1068/bach-air/bach-air-lys/bach-air-notes.ly'
P = F + 'BachJS/BWV1007/bwv1007/bwv1007-lys/bwv1007_prelude.ly'
SONGS = [
 dict(id='hallelujah', title='할렐루야 (메시아)', composer='G. F. 헨델', meterTxt='4/4', beatSym='♩', tp=92, dyn='f', nb=24, Q=4, key=2,
      kw='hallelujah messiah handel 할렐루야 메시아 에반게리온 evangelion', eva=True,
      parts={'v1': (H + 'violin1.ly', 'violinInotes'), 'v2': (H + 'violin2.ly', 'violinIInotes'), 'va': (H + 'viola.ly', 'violaNotes'),
             'vc': (H + 'cello.ly', 'celloNotes'), 's': (H + 'soprano.ly', 'SopNotes'), 'a': (H + 'alto.ly', 'AltoNotes'),
             't': (H + 'tenor.ly', 'TenorNotes'), 'b': (H + 'bass.ly', 'BassNotes'), 'tp': (H + 'trumpet.ly', 'trumpetI'), 'ti': (H + 'timpani.ly', 'timpaniNotes')},
      map={'mel': [['v1', 0]], 'har': [['v2', 0]], 'bass': [['vc', 0]], 'cb': [['vc', -12, 'beat']], 'pno': [['s', 0], ['a', 0], ['t', 0], ['b', 0], ['va', 0]],
           'fl': [['s', 12]], 'tpt': [['tp', 0]], 'timp': [['ti', 0]]},
      end=[38, 50, 57, 62, 66, 69, 74], src='Mutopia Project'),
 dict(id='air', title='G선상의 아리아 (관현악 모음곡 3번)', composer='J. S. 바흐', meterTxt='4/4', beatSym='♩', tp=56, dyn='p', nb=18, Q=4, key=2,
      kw='air on the g string bach orchestral suite 3 아리아 에어 에반게리온 evangelion', eva=True,
      parts={'v1': (A, 'violinone'), 'v2': (A, 'violintwo'), 'va': (A, 'viola'), 'bc': (A, 'continuo')},
      map={'mel': [['v1', 0]], 'har': [['v2', 0]], 'bass': [['bc', 0]], 'cb': [['bc', -12, 'beat']], 'pno': [['va', 0], ['bc', 0]],
           'fl': [['v1', 0]], 'tpt': [['va', 0]], 'timp': []},
      end=[38, 50, 57, 62, 66, 69, 74], src='Mutopia Project'),
 dict(id='celloprelude', title='무반주 첼로 모음곡 1번 전주곡', composer='J. S. 바흐', meterTxt='4/4', beatSym='♩', tp=76, dyn='mf', nb=22, Q=4, key=7,
      kw='cello suite 1 prelude bach 첼로 무반주 전주곡 신지 에반게리온 evangelion', eva=True,
      parts={'c': (P, 'prelude')},
      map={'bass': [['c', 0]], 'mel': [['c', 12]], 'har': [['c', 12, 'beat']], 'cb': [['c', -12, 'low']], 'pno': [['c', 0], ['c', -12, 'low']],
           'fl': [['c', 24]], 'tpt': [['c', 12, 'low']], 'timp': []},
      end=[43, 55, 62, 67, 71, 74, 79], src='Mutopia Project'),
]
out = []
for S in SONGS:
    limit = S['Q'] * S['nb']
    parts = {}
    for k, (f, v) in S['parts'].items():
        flat = []
        for t, d, p in parse(f, v, 'nederlands'):
            if t >= limit - 1e-9: continue
            d = min(d, limit - t)
            flat += [round(t * 96), max(1, round(d * 96)), p]
        parts[k] = flat
    # 끝 화음
    parts['end'] = [x for p in S['end'] for x in (limit * 96, S['Q'] * 96, p)]
    o = {k: S[k] for k in ('id', 'title', 'composer', 'meterTxt', 'beatSym', 'tp', 'dyn', 'key', 'kw', 'eva', 'map', 'src')}
    o.update(qPerBar=S['Q'], qPerBeat=1, nBars=S['nb'] + 1, parts=parts)
    out.append(o)
    print(S['id'], {k: len(v) // 3 for k, v in parts.items()}, file=sys.stderr)
print('const PART_SONGS=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';')
