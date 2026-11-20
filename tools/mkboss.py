import sys, json
sys.path.insert(0, '/home/claude/tools')
from lyparse import parse
F = '/home/claude/mutopiaproject/mutopiaproject/ftp/'
# id, 제목, 작곡가, 파일, 오른손, 왼손, 표기법, 마디(4분음표), 박(4분음표), 마디 수, 템포, 셈여림, 끝 화음(midi), 박자표, 키, 검색어
SONGS = [
 ('revolutionary', '혁명 에튀드 Op.10 No.12', 'F. 쇼팽', 'ChopinFF/O10/op-10-12-wfi/op-10-12-wfi.ly', 'rechts', 'links', 'deutsch', 4, 1, 40, 160, 'f',
  [36, 43, 48, 51, 55, 60, 63, 67], '4/4', 0, 'revolutionary etude chopin op 10 no 12 혁명 에튀드 연습곡'),
 ('etude1', '에튀드 Op.10 No.1', 'F. 쇼팽', 'ChopinFF/O10/chp-10-01/chp-10-01-lys/chp-10-01-a4.ly', 'MIDIrechts', 'MIDIlinks', 'deutsch', 4, 1, 28, 152, 'f',
  [36, 48, 55, 60, 64, 67, 72], '4/4', 0, 'etude chopin op 10 no 1 waterfall 폭포 에튀드 연습곡'),
 ('blackkey', '흑건 Op.10 No.5', 'F. 쇼팽', 'ChopinFF/O10/chp-10-05/chp-10-05-lys/chp-10-05-a4.ly', 'rechtsHAUPT', 'linksHAUPT', 'deutsch', 2, 1, 49, 116, 'mf',
  [42, 54, 61, 66, 70, 73, 78], '2/4', 6, 'black key etude chopin op 10 no 5 흑건 에튀드 연습곡'),
 ('moonlight3', '월광 소나타 3악장', 'L. v. 베토벤', 'BeethovenLv/O27/moonlight/moonlight-lys/moonlight3-a4.ly', 'topmain', 'bottom', 'nederlands', 4, 1, 40, 160, 'mf',
  [37, 49, 56, 61, 64, 68, 73], '4/4', 1, 'moonlight sonata 3rd movement beethoven presto agitato 월광 3악장'),
]
out = []
for sid, title, comp, f, rv, lv, lang, Q, qb, nb, tp, dyn, endch, meter, key, kw in SONGS:
    limit = Q * nb
    parts = {}
    for name, var in (('rh', rv), ('lh', lv)):
        ev = parse(F + f, var, lang)
        flat = []
        for t, d, p in ev:
            if t >= limit - 1e-9: continue
            d = min(d, limit - t)
            if not (21 <= p <= 108): continue
            flat += [round(t * 96), max(1, round(d * 96)), p]
        if name == 'rh':
            for p in endch:
                if p >= 60: flat += [limit * 96, Q * 96, p]
        else:
            for p in endch:
                if p < 60: flat += [limit * 96, Q * 96, p]
        parts[name] = flat
    out.append(dict(id=sid, title=title, composer=comp, meterTxt=meter, beatSym='♩', kw=kw, qPerBar=Q, qPerBeat=qb,
                    key=key, boss=True, nBars=nb + 1, tp=tp, dyn=dyn, parts=parts,
                    src='Mutopia Project LilyPond 악보'))
    print(sid, len(parts['rh']) // 3, len(parts['lh']) // 3, file=sys.stderr)
print('const BOSS_SONGS=' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';')
