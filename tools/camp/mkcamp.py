import json
M=json.load(open('/tmp/camp.json'))[:21]
# 수작업 보정(악보 이미지와 대조): 1마디 앞 쉼표 반영, 4마디는 8분음표+8분쉼표(96)로 5마디(192)와 합쳐 한 마디
fix={1:48}
rh,lh=[],[];off=0
for i,m in enumerate(M,1):
  L=288
  if i==4:L=96
  if i==5:L=192
  sh=fix.get(i,0)
  for s,dst in ((0,rh),(1,lh)):
    seen={}
    for t,d,p in m['staffs'][s]['notes']:
      t2=t+sh
      if t2>=L:continue
      k=(t2,p)
      if k not in seen or seen[k]<d: seen[k]=min(d,L-t2)
    for (t2,p),d in sorted(seen.items()): dst+= [off+t2,d,p]
  off+=L
print(off/288)
song={"id":"campanella","title":"라 캄파넬라","composer":"F. 리스트","meterTxt":"6/8","beatSym":"♩.",
 "kw":"la campanella liszt paganini etude 캄파넬라 리스트 파가니니","qPerBar":3,"qPerBeat":1.5,"key":8,"boss":True,
 "nBars":int(off/288),"tp":108,"dyn":"mf","parts":{"rh":rh,"lh":lh},"src":"pianoclassics.net 퍼블릭 도메인 악보"}
open('/tmp/camp.js','w').write(json.dumps(song,ensure_ascii=False,separators=(',',':')))
