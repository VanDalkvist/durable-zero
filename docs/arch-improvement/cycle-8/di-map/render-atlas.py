from pathlib import Path
import json,html,textwrap,collections,os
P=Path(os.environ.get('OUTPUT_DIR',str(Path(__file__).resolve().parent))).resolve(); D=json.loads((P/'bindings.json').read_text()); PK=json.loads((P/'package-dependencies.json').read_text())
COL={'public':'#34d399','lower':'#fbbf24','fixed':'#fb7185','dormant':'#94a3b8','native':'#60a5fa'}; ESC=html.escape
BG='#0b1220'; FG='#e2e8f0'; MUT='#a8b6cc'
def start(w,h,title,subtitle):
 return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{ESC(title)}"><defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="none" stroke="context-stroke" stroke-width="1.4"/></marker></defs><style>text{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;fill:{FG};font-size:16px}}.small{{font-size:13px;fill:{MUT}}}.title{{font-family:system-ui,sans-serif;font-size:29px;font-weight:700}}.head{{font-family:system-ui,sans-serif;font-size:20px;font-weight:600}}</style><rect width="100%" height="100%" fill="{BG}"/><text x="35" y="44" class="title">{ESC(title)}</text><text x="35" y="74" class="small">{ESC(subtitle)}</text>']
def line(g,x,y,txt,cls='',fill=None): g.append(f'<text x="{x}" y="{y}" class="{cls}"'+(f' style="fill:{fill}"' if fill else '')+f'>{ESC(txt)}</text>')
def wrapped(g,x,y,txt,width=43,limit=4,color=None):
 chunks=textwrap.wrap(txt,width=width,break_long_words=True,break_on_hyphens=False) or ['']
 for i,t in enumerate(chunks[:limit]): line(g,x,y+21*i,t,fill=color)
 return chunks
def node(g,x,y,w,h,title,body,color='#60a5fa',link=None):
 if link:g.append(f'<a href="{ESC(link,quote=True)}" target="_blank">')
 g.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#132034" stroke="{color}" stroke-width="1.7"/>')
 wrapped(g,x+15,y+25,title,width=max(15,int((w-30)/9.5)),limit=3 if not body else 2,color=color)
 wrapped(g,x+15,y+68,body,width=max(15,int((w-30)/9.5)),limit=max(2,int((h-60)/21)))
 if link:g.append('</a>')
def arrow(g,x1,y1,x2,y2,label='',color='#9cafc9',dash=False):
 g.append(f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="7 5"' if dash else '')+' marker-end="url(#arr)"/>')
 if label:line(g,(x1+x2)/2-20,(y1+y2)/2-9,label,'small',color)
def legend(g,y):
 x=35
 for s in ['public','lower','fixed','dormant','native']:
  label={'public':'G: явная передача','lower':'Y: нижний API','fixed':'R: выбор зашит','dormant':'D: не подключено','native':'N: native owner'}[s]
  g.append(f'<rect x="{x}" y="{y-13}" width="12" height="12" rx="2" fill="{COL[s]}"/>');line(g,x+20,y,label,'small');x+=320
 line(g,35,y+28,'Цвет = способ подключения, не итог тестов. Низкий уровень API не равен assembleDurableZero().','small')
def save(name,g):
 (P/name).write_text('\n'.join(g+['</svg>']))
# Switchboard pages: every recorded component gets its own concrete route, consumer and source.
pages=[]
for key,title,statuses in [('public','02 · Где DI / внешнее подключение уже есть',['public']),('lower','03 · Частично: нижний API есть, верхний recipe не пропускает',['lower']),('fixed','04 · Где выбор зашит; отдельно намеренные native owners',['fixed','native']),('dormant','05 · Контракты и модули, не включённые в штатный startup',['dormant'])]:
 rows=[r for r in D['bindings'] if r['status'] in statuses]; h=220+len(rows)*226;g=start(1700,h,title,'Текущий PR85afe89 · читайте каждую строку слева направо · подробные ограничения и файлы в atlas.html');legend(g,108)
 for x,t in [(35,'1. Где передаётся / где выбор зашит'),(610,'2. Что выбрано сейчас'),(1185,'3. Реальный потребитель')]:line(g,x,183,t,'head')
 for i,r in enumerate(rows):
  y=204+i*226;c=COL[r['status']]; badge={'public':'G','lower':'Y','fixed':'R','dormant':'D','native':'N'}[r['status']]
  node(g,35,y,480,137,badge+' · '+r['name'],r['entry'],c,r['evidence'][0]['url']);node(g,610,y,480,137,r['implementation'],'',c);node(g,1185,y,480,137,r['consumer'],'',c)
  arrow(g,520,y+65,605,y+65,'',c,r['status']=='dormant');arrow(g,1095,y+65,1180,y+65,'',c,r['status']=='dormant')
  if r['status']=='dormant':line(g,1102,y+57,'×','head',c)
  wrapped(g,45,y+164,r['limitation'],width=161,limit=2)
  e=r['evidence'][0];line(g,45,y+211,f"{e['file']}:{e['line']}",'small')
 save(key+'.svg',g);pages.append({'id':key,'title':title,'file':key+'.svg'})
# Runtime/process overview: actual request path, not package import direction.
g=start(1700,930,'01 · Кто запускает и кто исполняет','Фактические процессы и сообщения · prompt возвращает admission, результат приходит событиями · не graph imports');legend(g,108)
g.append('<rect x="30" y="178" width="400" height="670" rx="14" fill="none" stroke="#40546f" stroke-dasharray="8 5"/><rect x="460" y="178" width="1210" height="670" rx="14" fill="none" stroke="#40546f" stroke-dasharray="8 5"/>')
line(g,50,211,'Клиентский процесс','head');line(g,480,211,'Процесс runtime / session owner','head')
node(g,60,245,340,115,'local-terminal','ZeroTerminalClient + terminal-ui',COL['public'])
node(g,510,245,340,115,'local-runtime','Unix socket JSON-RPC; admission / reload queue',COL['native'])
node(g,900,245,340,115,'runner','assembleDurableZero(); одна готовая сборка',COL['native'])
node(g,900,450,340,115,'core','SessionCoordinator → IAgentEngine',COL['public'])
node(g,1290,450,340,115,'adapter-pi-durable','PiDurableEngine → openDurable()',COL['public'])
node(g,1290,675,340,125,'SDK Harness + Chord','Единственный model/tool/session execution owner',COL['native'])
node(g,510,675,340,125,'ModelRuntime + Registry','LLM providers, builtin / extension tools',COL['lower'])
node(g,900,675,340,125,'ExecutionEnvs + SQLite','IO фабрика; native session storage',COL['native'])
arrow(g,405,305,505,305,'RPC');arrow(g,855,305,895,305,'создаёт');arrow(g,1070,365,1070,445,'prompt');arrow(g,1245,510,1285,510,'engine.submit',COL['public']);arrow(g,1460,570,1460,670,'native submit',COL['native']);arrow(g,1285,737,1245,737,'env/storage');g.append('<path d="M1395 670 L1395 625 L680 625 L680 670" fill="none" stroke="#fbbf24" stroke-width="2" marker-end="url(#arr)"/>');line(g,725,615,'Harness: models / registry tools','small',COL['lower'])
g.append('<path d="M1460 802 L1460 875 L230 875 L230 365" fill="none" stroke="#34d399" stroke-dasharray="8 5" stroke-width="2" marker-end="url(#arr)"/>');line(g,475,900,'Native state/events → local-runtime notifications → ZeroTerminalClient → UI','small',COL['public'])
line(g,60,415,'Альтернативный вход:','head');wrapped(g,60,450,'cli → runner/main.ts → assembleDurableZero(); тот же backend через stdio',width=32,limit=5)
line(g,510,410,'local-runtime требует native view/controller;','small');line(g,510,435,'custom IAgentEngine сам по себе их не даёт.','small')
save('runtime.svg',g);pages.insert(0,{'id':'runtime','title':'01 · Реальный runtime и сообщения','file':'runtime.svg'})
# Full workspace dependency matrix: exact AST-derived edges, no invented runtime path.
ids=[p['id'] for p in PK['packages']];w=1700; h=1090;g=start(w,h,'06 · Все зависимости workspace-пакетов','Строка зависит от колонки · S: source import/export/resolve · T: только type · M: только manifest · tests/dist исключены')
cell=51;left=420;top=350
for j,n in enumerate(ids):g.append(f'<text x="{left+j*cell+30}" y="{top-15}" transform="rotate(-55 {left+j*cell+30} {top-15})" class="small">{ESC(n)}</text>')
lookup={(e['from'],e['to']):e for e in PK['edges']}
for i,a in enumerate(ids):
 line(g,35,top+i*cell+31,a)
 for j,b in enumerate(ids):
  x=left+j*cell;y=top+i*cell;e=lookup.get((a,b));fill='#172238';stroke='#24344b';letter='·';c='#516076'
  if e:letter={'source':'S','type':'T','manifest-only':'M'}[e['kind']];c={'source':'#34d399','type':'#60a5fa','manifest-only':'#a8b6cc'}[e['kind']];stroke=c
  if a==b:letter='—'
  g.append(f'<rect x="{x}" y="{y}" width="47" height="47" rx="5" fill="{fill}" stroke="{stroke}"/><text x="{x+18}" y="{y+31}" style="fill:{c}">{letter}</text>')
node(g,1155,355,500,200,'Важно: это не runtime-flow','Source import не доказывает исполнение. Type-only import не является runtime-call. Manifest-only dependency не означает подключённый модуль.','#60a5fa')
node(g,1155,590,500,260,'Что здесь особенно показательно','runner → adapter-pi-ai / execution: M. extension-pi-resource → core / adapter-pi-durable: M. adapter-codemode → engine: T (контракт BuiltinExtension).','#fbbf24')
save('packages.svg',g);pages.append({'id':'packages','title':'06 · Все workspace package dependencies','file':'packages.svg'})
# Direct SDK/runtime imports, including actual type-only edges. Node built-ins are not npm dependencies.
external=collections.defaultdict(list)
for ref in PK['externalReferences']:
 target=ref['to']
 if target.startswith('node:') or target in ['fs','path','os','util','events','stream','url','module','buffer','child_process','crypto','readline','tty','net','http','https','assert','string_decoder']: target='Node built-ins'
 external[(ref['from'],target)].append(ref)
cols=sorted({b for a,b in external});g=start(1800,1200,'07 · Прямые зависимости на SDK и другие библиотеки','Это source imports / exports / resolve, не все транзитивные npm dependencies. Node built-ins сгруппированы, не считаются npm packages.')
cell=62;left=430;top=400
for j,name in enumerate(cols):
 short=name.replace('@earendil-works/','')
 g.append(f'<text x="{left+j*cell+25}" y="{top-15}" transform="rotate(-55 {left+j*cell+25} {top-15})" class="small">{ESC(short)}</text>')
for i,a in enumerate(ids):
 line(g,35,top+i*cell+31,a)
 for j,b in enumerate(cols):
  refs=external.get((a,b),[]);kind='S' if any(r['kind']!='type' for r in refs) else 'T' if refs else '·';c='#34d399' if kind=='S' else '#60a5fa' if kind=='T' else '#3b4b64';x=left+j*cell;y=top+i*cell
  if refs:
   r=refs[0];g.append(f'<a href="https://github.com/VanDalkvist/durable-zero/blob/{D["sourceSha"]}/{r["file"]}#L{r["line"]}" target="_blank">')
  g.append(f'<rect x="{x}" y="{y}" width="56" height="47" rx="5" fill="#172238" stroke="{c}"/><text x="{x+21}" y="{y+31}" style="fill:{c}">{kind}</text>')
  if refs:g.append('</a>')
save('external.svg',g);pages.append({'id':'external','title':'07 · Прямые SDK / library imports','file':'external.svg'})
# Mermaid companions, loadable directly by BB Diagram. Smaller scoped views instead of one hairball.
style='\nclassDef public fill:#0d3328,stroke:#34d399,color:#ecfdf5;\nclassDef lower fill:#392d12,stroke:#fbbf24,color:#fffbeb;\nclassDef fixed fill:#3b1923,stroke:#fb7185,color:#fff1f2;\nclassDef dormant fill:#202c40,stroke:#94a3b8,color:#e2e8f0;\nclassDef native fill:#142c4d,stroke:#60a5fa,color:#eff6ff;'
def label(s):return s.replace('"',"'").replace('\n','<br/>')
graphs={}
for key,title,statuses in [('public','Готовая явная DI / подключение',['public']),('lower','Нижние native seams',['lower']),('fixed','Фиксированные подключения',['fixed','native']),('dormant','Не mounted в штатной сборке',['dormant'])]:
 rs=[r for r in D['bindings'] if r['status'] in statuses]; m='flowchart LR\n'; details={}
 for idx,r in enumerate(rs):
  a='p'+str(idx);b='v'+str(idx);arrowcode='-.->' if r['status']=='dormant' else '-->'
  m+=f'  {a}["{label(r["name"])}<br/>{label(r["entry"])}"] {arrowcode}|{"нет mount" if r["status"]=="dormant" else "потребитель"}| {b}["{label(r["consumer"])}"]\n  class {a},{b} {r["status"]};\n'
  text='**'+r['name']+'**\n\n'+r['how']+'\n\n**Ограничение:** '+r['limitation']+'\n\n**Проверка:** '+r['verification']+'\n\n'+'\n'.join(f"[{e['file']}:{e['line']}]({e['url']})" for e in r['evidence']); details[a]=text;details[b]=text
 graphs[key]={'title':title,'mermaid':m+style,'details':details}
packageM='flowchart LR\n'
for p in PK['packages']:packageM+=f'  {p["id"].replace("-","_")}["{p["id"]}"]\n'
for e in PK['edges']:
 a=e['from'].replace('-','_');b=e['to'].replace('-','_');typ={'source':'source','type':'type','manifest-only':'manifest'}[e['kind']];ar='-->' if typ=='source' else '-.->';packageM+=f'  {a} {ar}|{typ}| {b}\n'
graphs['packages']={'title':'Все workspace package dependencies','mermaid':packageM,'details':{p['id'].replace('-','_'):'**'+p['name']+'**\n\n'+ '\n'.join(f"→ {e['to']}: {e['kind']}" for e in PK['edges'] if e['from']==p['id']) for p in PK['packages']}}
runtime='''flowchart TB
  CLI["cli / runner/main.ts"] -->|assemble| ROOT["runner: assembleDurableZero"]
  TUI["terminal-ui + ZeroTerminalClient"] -->|Unix socket JSON-RPC| HOST["local-runtime: startRuntime"]
  HOST -->|assemble| ROOT
  ROOT -->|engine injection| CORE["core: SessionCoordinator"]
  CORE -->|submit / abort / state| ENGINE["adapter-pi-durable: PiDurableEngine"]
  ENGINE -->|openDurable| HARNESS["Native Harness + Chord"]
  HARNESS -->|models| MODEL["Pi ModelRuntime"]
  HARNESS -->|tools| REG["Native Registry"]
  HARNESS -->|env callback| ENV["ExecutionEnvs: Core or native factory"]
  HARNESS -->|storage| DB["Native SQLite session"]
  HARNESS -.->|state / events via adapter| HOST
  HOST -.->|notifications| TUI
  class ROOT,HOST,HARNESS,DB native;
  class CORE,ENGINE,ENV public;
  class MODEL,REG lower;
'''+style
graphs['runtime']={'title':'Runtime: процессы и сообщения, не package imports','mermaid':runtime,'details':{'ROOT':D['bindings'][0]['evidence'][0]['url'],'ENGINE':'Native ports доступны только в default native branch сборки. Generic engine не обеспечивает готовый terminal host.','HARNESS':'Единственный execution owner. Prompt возвращает admission receipt; результат поступает через события.','REG':'Coding tools / subagents hardwired; дополнительные builtins и Pi tools регистрируются отдельно.','ENV':'Реальные factory calls находятся в ExecutionEnvs.getOrCreate; Core и Native варианты взаимоисключающие.','HOST':'Socket transport и lifecycle owner, не второй model loop.'}}
sequence='''sequenceDiagram
  participant U as terminal-ui
  participant C as ZeroTerminalClient
  participant S as local-runtime
  participant R as runner / stdio
  participant K as Core coordinator
  participant E as PiDurableEngine
  participant H as Native Harness
  U->>C: submit(content)
  C->>S: session/prompt (Unix JSON-RPC)
  S->>R: bridge.request(session/prompt)
  R->>K: prompt(content, options)
  K->>E: submit(input, options)
  E->>H: native controller.submit
  H-->>E: submission / admission
  E-->>K: PromptAdmissionReceipt
  K-->>R: receipt
  R-->>S: RPC response
  S-->>C: RPC response
  Note over H: Model/tool work belongs to native runtime, not another Zero loop
  H-->>E: state / task / entry updates
  E-->>S: native view + coordinator events
  S-->>C: session/view + session/event notifications
  C-->>U: subscribed view update
'''
graphs['interaction']={'title':'Один prompt: admission отдельно от последующих событий','mermaid':sequence,'details':{}}
(P/'diagrams.json').write_text(json.dumps(graphs,ensure_ascii=False,indent=2)+'\n')
for k,v in graphs.items():(P/(k+'.mmd')).write_text(v['mermaid'].rstrip()+'\n')
# Offline HTML artifact. Plain SVG + CSS, no remote fonts/scripts or runtime dependencies.
stylehtml='''body{margin:0;background:#0b1220;color:#e2e8f0;font:16px/1.55 system-ui,sans-serif}main{max-width:1760px;margin:auto;padding:28px}h1{font-size:32px;margin:0}h2{margin-top:45px}a{color:#93c5fd}nav{display:flex;flex-wrap:wrap;gap:10px;padding:20px 0}nav a{padding:7px 12px;border:1px solid #3b4b64;border-radius:8px;text-decoration:none}p{max-width:1100px}.meta{color:#a8b6cc}.diagram{overflow:auto;border:1px solid #3b4b64;border-radius:12px}.diagram img{display:block;width:100%;min-width:1100px;height:auto}details{padding:15px;border:1px solid #334155;margin:12px 0;border-radius:9px}summary{font-weight:650;cursor:pointer}.legend{display:flex;gap:20px;flex-wrap:wrap}.legend span{padding:4px 10px;border:1px solid;border-radius:7px}code{color:#bae6fd}li{margin:8px 0}section{scroll-margin-top:15px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #334155;padding:10px;text-align:left;vertical-align:top}th{background:#142034}footer{color:#a8b6cc;margin:40px 0}'''
body=['<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Zero · Карта DI и подключений</title><style>'+stylehtml+'</style><main><h1>Zero / Durable Zero · карта реальных подключений</h1><p class="meta">Исходники PR #3: '+D['sourceSha']+' · '+D['date']+' · только анализ, без изменений кода продукта</p><p>Это карта текущего кода, не будущий дизайн. Сначала процессы, затем все механизмы замены по уровню доступности. Зелёный — существующий параметр и реальный потребитель, не сертификат полной работоспособности. Выбор LLM и файлов настроек показан отдельно от DI.</p><nav>'+''.join(f'<a href="#{p["id"]}">{ESC(p["title"])}</a>' for p in pages)+'<a href="#inventory">Все точки замены + evidence</a></nav>']
for page in pages:
 body.append(f'<section id="{page["id"]}"><h2>{ESC(page["title"])}</h2><div class="diagram"><img src="{page["file"]}" alt="{ESC(page["title"])}"></div></section>')
body.append('<section id="inventory"><h2>Все точки замены: что именно можно сделать</h2>')
for r in D['bindings']:
 c=COL[r['status']];body.append(f'<details id="binding-{r["id"]}"><summary style="color:{c}">{ESC(D["legend"][r["status"]]["label"])} · {ESC(r["name"])}</summary><p><b>Вход:</b> <code>{ESC(r["entry"])}</code></p><p><b>Сейчас:</b> {ESC(r["implementation"])} → {ESC(r["consumer"])}</p><p><b>Как заменить:</b> {ESC(r["how"])}</p><p><b>Ограничение:</b> {ESC(r["limitation"])}</p><p><b>Проверка:</b> {ESC(r["verification"])}</p><ul>'+''.join(f'<li><a href="{e["url"]}">{ESC(e["file"])}:{e["line"]}</a><br><code>{ESC(e["quote"])}</code></li>' for e in r['evidence'])+'</ul></details>')
body.append('</section><section><h2>Что является настройкой, а не заменой реализации</h2><ul>'+''.join('<li><b>'+ESC(x['name'])+'</b>: '+ESC(x['route'])+' — '+ESC(x['meaning'])+'</li>' for x in D['configurationNotDi'])+'</ul></section><section><h2>Почему здесь несколько схем</h2><p>По C4/arc42: статические зависимости, сборочная конфигурация и runtime-сообщения — разные виды. Нельзя читать стрелку импорта как поток исполнения. Type-only и manifest-only зависимости не рисуются как активное runtime-подключение.</p><ul>'+''.join('<li><a href="'+x['url']+'">'+ESC(x['title'])+'</a></li>' for x in D['methodSources'])+'</ul><p>Область охвата: '+ESC(D['scope'])+'</p></section><footer>Source-traced atlas. Внешние сервисы/модели не запускались. Source status не подменяет acceptance tests. Код графиков и JSON доступны рядом.</footer></main></html>')
(P/'atlas.html').write_text('\n'.join(body));(P/'pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'svgPages':len(pages),'bindingRows':len(D['bindings']),'mermaidViews':list(graphs),'html':'atlas.html'}))
