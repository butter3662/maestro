# MuseScore 2 벡터 PDF에서 음표 위치를 읽어 [q96,d96,midi] 로 변환 (PDF는 데이터로만 읽음)
import pymupdf as fitz, sys, json
from collections import defaultdict
PDF=sys.argv[1];import os;DBG=int(os.environ.get('DBG','0'))
HEAD={'0xe12d':'b','0xe12c':'h','0xe12b':'w'}
DOT='0xe127'
ACC={'0xe10e':1,'0xe11c':2,'0xe113':0,'0xe114':-1,'0xe11a':-2}   # sharp, double sharp, natural, flat, double flat
REST={'0xe100':'bar','0xe101':192,'0xe107':96,'0xe109':48,'0xe10a':24}
FLAG={'0xe190':1,'0xe194':1,'0xe191':2,'0xe195':2,'0xe197':2,'0xe192':3,'0xe196':3}
CLEF={'0xe19e':'G','0xe19c':'F'}
BAR=288
def polyY(pts,x):
  ys=[]
  for i in range(len(pts)):
    (x1,y1),(x2,y2)=pts[i],pts[(i+1)%len(pts)]
    if min(x1,x2)-1e-6<=x<=max(x1,x2)+1e-6 and abs(x2-x1)>1e-6: ys.append(y1+(y2-y1)*(x-x1)/(x2-x1))
  return (min(ys),max(ys)) if ys else None
def page(pg,pi):
  # 1) 오선 간격으로 배율 Z 구하고 모든 좌표를 캄파넬라 악보(줄 간격 4pt) 크기로 맞춘다
  Z=None
  for dr in pg.get_drawings():
    it=dr['items']
    if dr['type']=='s' and len(it)==5 and all(i[0]=='l' for i in it):
      Z=(it[4][1].y-it[0][1].y)/16;break
  if Z is None: return []
  G=defaultdict(list);TUP=[]
  for b in pg.get_text('rawdict')['blocks']:
    for l in b.get('lines',[]):
      for s in l['spans']:
        if s['font'].startswith(('MScore','Bravura')):
          for ch in s['chars']:
            k=hex(ord(ch['c']));x,y=ch['origin'];G[k].append((x/Z,y/Z,s['size']/Z,(ch['bbox'][2]-ch['bbox'][0])/Z))
        elif 'Italic' in s['font'] or (s['font'].startswith('FreeSerif') and 8.5/Z < s['size']/Z < 11/Z and abs(s['size']-8)>0.5):
          for ch in s['chars']:
            if ch['c']=='3': TUP.append((ch['origin'][0]/Z,ch['origin'][1]/Z))
  staffs={};stems=[];beams=[];bars=[];otta=[]
  for dr in pg.get_drawings():
    it=dr['items'];w=round((dr.get('width') or 0)/Z,2)
    if dr['type']=='s' and len(it)==5 and all(i[0]=='l' for i in it):
      ys=tuple(round(i[1].y/Z,1) for i in it);x0=min(i[1].x for i in it)/Z;x1=max(i[2].x for i in it)/Z
      k=ys[0];o=staffs.get(k);staffs[k]=(ys,min(x0,o[1]) if o else x0,max(x1,o[2]) if o else x1)
    elif dr['type']=='s' and len(it)==1 and it[0][0]=='l':
      p,q=it[0][1],it[0][2]
      px,py,qx,qy=p.x/Z,p.y/Z,q.x/Z,q.y/Z
      if abs(px-qx)<.2 and .47<w<.57: stems.append((px,min(py,qy),max(py,qy)))
      elif abs(px-qx)<.2 and .59<w<.69: bars.append((px,min(py,qy),max(py,qy)))
      elif abs(py-qy)<.2 and .35<w<.45: otta.append((min(px,qx),max(px,qx),py))
    elif dr['type']=='f' and len(it)==4 and all(i[0]=='l' for i in it):
      pts=[(i[1].x/Z,i[1].y/Z) for i in it]; beams.append(pts)
  st=sorted(staffs.values(),key=lambda s:s[0][0])
  systems=[(st[i],st[i+1]) for i in range(0,len(st)-1,2)]
  out=[]
  for si,(top,bot) in enumerate(systems):
    y0,y1=top[0][0],bot[0][4]
    bx=sorted({round(b[0],1) for b in bars if b[1]<=y0+1 and b[2]>=y1-1})
    # 같은 위치 두 줄(겹세로줄) 정리
    bxs=[];[bxs.append(x) for x in bx if not bxs or x-bxs[-1]>3]
    def near(y,ss):
      a,b=ss[0][0],ss[0][4];return 0 if a<=y<=b else min(abs(y-a),abs(y-b))
    def staffOf(y):
      j=min(range(len(st)),key=lambda j:near(y,st[j]))
      return {2*si:0,2*si+1:1}.get(j,-1)
    S=[top,bot]
    clefs=[[],[]]
    for k in CLEF:
      for x,y,sz,_ in G[k]:
        if y0-30<y<y1+30: clefs[staffOf(y)].append((x,k))
    for c in clefs:c.sort()
    sysx0=min(x for c in clefs for x,_ in c)
    def clefAt(s,x):
      c=[k for cx,k in clefs[s] if cx<x];return CLEF[c[-1]] if c else None
    heads=[(x,y,k,sz,w) for k in HEAD for x,y,sz,w in G[k] if y0-40<y<y1+40 and sz>15]
    firstNote=[min([x for x,y,*_ in heads if staffOf(y)==s] or [9e9]) for s in (0,1)]
    # 조표
    key=[0,0]
    # 조표: 음자리표 바로 뒤(16 이내)에서 시작해 6 간격 이내로 이어지는 변화표 묶음
    for s_ in (0,1):
      cx=[x for x,_ in clefs[s_] if x<sysx0+5]
      if not cx: continue
      c0=min(cx);acc=[]
      for gk,sg in (('0xe10e',1),('0xe114',-1),('0xe113',0)):
        for x,y,*_ in G[gk]:
          if y0-30<y<y1+30 and staffOf(y)==s_ and c0<x<c0+60: acc.append((x,sg))
      acc.sort();n=0;last=None
      for x,sg in acc:
        if last is None and x>c0+18: break
        if last is not None and x-last>6.5: break
        if sg: n+=sg
        last=x
      key[s_]=n
    # 옥타브 선
    ott=[]
    for a,b,y in otta:
      s=None
      if y<top[0][0] and y>top[0][0]-80 and (si==0 or y>systems[si-1][1][0][4]): s=0
      if s is None:continue
      g=[gx for gx,gy,*_ in G['0xe510'] if abs(gy-y)<8 and a-25<gx<=a+2]
      ott.append((min(g) if g else a,b,s,12))
    for gx,gy,*_ in G['0xe510']:
      if y0-80<gy<top[0][0] and not any(a<=gx+1 and gx-1<=b for a,b,_,_ in ott):
        ott.append((gx,gx+6,0,12))   # 선 없는 짧은 8va
    bounds=[sysx0]+bxs
    for mi in range(len(bounds)-1):
      xa,xb=bounds[mi],bounds[mi+1]
      if xb-xa<15:continue
      meas={'page':pi,'sys':si,'staffs':[]}
      for s in (0,1):
        ys=S[s][0];sp=(ys[4]-ys[0])/4;yb=ys[4]
        evs=[]
        acc_state={}
        if s==0: allev=[]
        hs=sorted([h for h in heads if xa<h[0]<xb and staffOf(h[1])==s])
        # 음표머리 → 기둥
        groups=defaultdict(list)
        for x,y,k,sz,w in hs:
          hit=[i for i,(sx,sy0,sy1) in enumerate(stems) if (abs(sx-(x+w))<1.2 or abs(sx-x)<1.2) and sy0-1.5<=y<=sy1+1.5]
          if not hit: groups[('h',round(x,1),round(y,1))].append((x,y,k,w))
          for i in hit: groups[('s',i)].append((x,y,k,w))
        for gk,notes in groups.items():
          xs=min(n[0] for n in notes)
          if gk[0]=='s':
            sx,sy0,sy1=stems[gk[1]]
            ups=[n for n in notes if abs(sx-(n[0]+n[3]))<1.2]
            up=sy0<min(n[1] for n in notes)-2
            xs=sx-notes[0][3] if up else sx
            nb=0
            for pts in beams:
              r=polyY(pts,sx)
              if r and r[1]>=sy0-1.5 and r[0]<=sy1+1.5: nb+=1
            nf=0
            for fk,fv in FLAG.items():
              for fx,fy,fsz,_ in G[fk]:
                if fsz>15 and abs(fx-sx)<1.5 and (abs(fy-sy0)<4 or abs(fy-sy1)<4): nf=max(nf,fv)
            n=max(nb,nf)
            dur=96>>n if n else (192 if HEAD[notes[0][2]]=='h' else 96)
          else:
            dur=384 if HEAD[notes[0][2]]=='w' else 192
          if any(any(x+w+.2<dx<x+w+7 and abs(dy-y)<2.6 for dx,dy,*_ in G[DOT]) for x,y,k,w in notes): dur=dur*3//2
          pitches=[]
          for x,y,k,w in notes:
            step=round((yb-y)/(sp/2))
            c=clefAt(s,x)
            dia=(30 if c=='G' else 18)+step
            letter=dia%7;octv=dia//7
            base=[0,2,4,5,7,9,11][letter]+12*(octv+1)
            # 임시표
            a=None
            for ak,av in ACC.items():
              for ax,ay,asz,_ in G[ak]:
                if asz>15 and x-14<ax<x-1 and abs(ay-y)<1.2: a=av
            if a is not None: acc_state[dia]=a
            if dia in acc_state: alt=acc_state[dia]
            elif key[s]>=0: alt=1 if letter in [3,0,4,1,5,2,6][:key[s]] else 0
            else: alt=-1 if letter in [6,2,5,1,4,0,3][:-key[s]] else 0
            o=sum(v for a2,b2,s2,v in ott if s2==s and a2-1<=x<=b2+3)
            pitches.append(base+alt+o)
          info=None
          if gk[0]=='s':
            sx,sy0,sy1=stems[gk[1]];info=(sx,sy0 if up else sy1)
          evs.append([xs,dur,sorted(pitches),s,info])
        for rk,rv in REST.items():
          for rx,ry,rsz,_ in G[rk]:
            if rsz>15 and xa<rx<xb and staffOf(ry)==s and abs(ry-(ys[0]+ys[4])/2)<3*sp and rv!='bar':
              rd=rv
              if any(rx+.5<dx<rx+9 and abs(dy-ry)<5 for dx,dy,*_ in G[DOT]): rd=rd*3//2
              evs.append([rx,rd,[],s,None])
        if len(evs)==1 and not evs[0][2]: evs=[]   # 단독 쉼표 = 마디 전체 쉼
        allev.extend(evs)
        meas['staffs'].append({'key':key[s]})
      for tx,ty in TUP:
        if not(xa<tx<xb) or not(y0-60<ty<y1+60): continue
        c=[e for e in allev if e[4] and abs(e[4][1]-ty)<16 and abs(e[4][0]-tx)<26 and not e[5:]]
        c.sort(key=lambda e:abs(e[4][0]-tx))
        if not c: continue
        st0=c[0][3];c=[e for e in c if e[3]==st0]
        # 같은 박(열)끼리 묶인 화음은 한 덩어리로: x가 다른 기둥 3개
        picked=[];xs_=[]
        for e in c:
          if any(abs(e[0]-x2)<3 for x2 in xs_): picked.append(e);continue
          if len(xs_)<3: xs_.append(e[0]);picked.append(e)
        for e in picked: e[1]=e[1]*2/3; e.append('t')
      evs=sorted(allev,key=lambda e:e[0])
      if True:
        # 같은 시점(세로 정렬) 묶어 시간 진행
        segs=[]
        for e in evs:
          if segs and abs(e[0]-segs[-1][0])<float(os.environ.get('TOL','6.5')): segs[-1][1].append(e)
          else: segs.append([e[0],[e]])
        if DBG and len(out)+1==DBG: print([(round(x,1),[(e[1],e[2],e[3]) for e in es]) for x,es in segs])
        t=0;ends=[];res=[[],[]]
        RS=[e for e in evs if not e[2]]
        segs=[sg for sg in segs if any(e[2] for e in sg[1])]
        for sg in segs: sg[1]=[e for e in sg[1] if e[2]]
        # 음표 열과 같은 x에 있는 쉼표는 그 열에서 시작하는 쉼으로 본다
        RS2=[]
        for e in RS:
          nseg=[sg for sg in segs if abs(sg[0]-e[0])<3.5]
          if nseg and e[0]>=segs[0][0]-2: nseg[0][1].append(e)
          elif segs and e[0]>segs[0][0]: segs.append([e[0],[e]])   # 홀로 선 쉼표 = 자기 열
          else: RS2.append(e)
        segs.sort(key=lambda sg:sg[0])
        RS=RS2
        if segs:
          x0=segs[0][0];lead=[]
          for s3 in (0,1):
            if any(e[3]==s3 and e[2] for e in segs[0][1]): lead.append(0);continue
            lead.append(sum(e[1] for e in RS if e[3]==s3 and e[0]<x0-2)+sum(e[1] for e in segs[0][1] if e[3]==s3 and not e[2]))
          t=min(lead); ends.extend(lead)
        for si2,(x,es) in enumerate(segs):
          for e in es:
            ends.append(t+e[1])
            for m in e[2]: res[e[3]].append((t,e[1],m))
          nx=[v for v in ends if v>t]
          if nx: t=min(nx)
          else:
            xn=segs[si2+1][0] if si2+1<len(segs) else 9e9
            rr=[e[1] for e in RS if x-2<e[0]<xn-2]
            t+= min(rr) if rr else 0
            ends.append(t)
        L=max(ends) if ends else 0
        for s2 in (0,1):
          meas['staffs'][s2]['notes']=res[s2]
          meas['staffs'][s2]['len']=max([a+b for a,b,_ in res[s2]]+[0])
        meas['len']=L
      out.append(meas)
  return out
d=fitz.open(PDF);allm=[]
for pi,pg in enumerate(d):allm+=page(pg,pi)
json.dump(allm,open(sys.argv[2],'w'))
for i,m in enumerate(allm):
  L=[s['len'] for s in m['staffs']];k=[s['key'] for s in m['staffs']]
  print(i+1,'p',m['page']+1,'sys',m['sys'],m['len'],L,k, '' if m['len']==int(os.environ.get('BARLEN','288')) else '<<')
print('measures',len(allm))
