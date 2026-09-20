"""Setter sammen template.html, modellresultatet og grunnkartene til én HTML-fil per område.
Bruk: python build.py            (alle områder under areas/)
      python build.py areas/skarnes"""
import json, re, base64, os, sys, glob
TXT={
 "alle":("Viser hvor du kan vente flest matsopparter på samme tur. Verdien er summen av sannsynlighetene for de tolv matsoppene i hvert punkt.","",0),
 "kantarell":("Mosegrodd gran- og bjørkeskog, ofte i skråninger og langs gamle stier. Den kommer igjen på samme sted år etter år.","Forveksles med falsk kantarell, som har tynne, ekte skiver og er en dårlig matsopp. Kantarellen har nedløpende ribber.",0),
 "traktkantarell":("Eldre, fuktig granskog med tykk mose og blåbærlyng, gjerne nordvendt. Kommer i store mengder fra september og til frosten.","Spiss giftslørsopp vokser på de samme stedene og er dødelig giftig. Se på hver eneste sopp: traktkantarell har ribber, hul stilk og traktformet hatt.",1),
 "steinsopp":("Granskog og blandingsskog med bjørk, ofte langs stier, i skogkanter og lysninger.","Forveksles med gallerørsopp, som er bitter, får rosa rørlag og har mørkt årenett på stilken.",0),
 "piggsopp":("Mosegrodd gran- og blandingsskog. Piggene under hatten gjør den til en av de sikreste matsoppene.","Ingen giftige forvekslingsarter.",0),
 "granmatriske":("Bare under gran, helst yngre gran langs stier og gresskledde kanter. Oransje melkesaft som blir grønnflekket.","Skjeggriske har hvit, brennende melkesaft og lodden hattkant, og er giftig rå.",0),
 "skrubb":("Under bjørk i skogkanter, langs stier og i blandingsskog med løvinnslag.","All skrubb må stekes eller kokes godt, minst 15 minutter. Rå eller dårlig varmebehandlet skrubb gir mageforgiftning.",1),
 "svartbrun":("Sur, næringsfattig barskog, både furu på kollene og eldre gran. Rørene blåner ved trykk.","Ligner mest på andre spiselige rørsopper.",0),
 "rimsopp":("Næringsfattig furu- og granskog med blåbærlyng, ofte på koller og rygger.","Hører til slørsoppene, der flere arter er giftige. Rimsopp har ring på stilken og rimaktig belegg på hatten. Bare for sikre plukkere.",1),
 "faresopp":("Eldre, mosegrodd granskog på litt rikere grunn. Vokser ofte i tette grupper.","Ligner franskbrødsopp, som også er spiselig. Fåresopp gulner ved steking.",0),
 "trompet":("Rik løvskog med hassel og eik på kalkrik grunn.","Ingen giftige forvekslingsarter.",0),
 "sandsopp":("Tørr furuskog på koller og grunnlendte rygger.","Middelmådig matsopp, men uten giftige forvekslingsarter.",0),
 "blodror":("Sur granskog og blandingsskog. Mørkebrun hatt, røde rørmunninger og kjøtt som blåner kraftig.","Må varmebehandles godt. Kan forveksles med andre rørsopper med røde rørmunninger. Bare for sikre plukkere.",1),
 "giftslor":("Fuktig, mosegrodd granskog, de samme stedene som traktkantarell. Kartet viser hvor du bør være ekstra nøye med kurven.","Dødelig giftig. Skader nyrene, og symptomene kommer først etter 2 til 14 dager.",1),
 "hvitflue":("Sur gran- og blandingsskog med bjørk. Helt hvit sopp med ring, og knoll i en pose nederst på stilken.","Dødelig giftig. Forveksles med sjampinjonger og andre hvite skivesopper. Grav alltid opp hele stilken på hvite sopper.",1)}
css=open('assets/leaflet.css').read(); css=re.sub(r'[^{};]*url\([^)]*\)[^;}]*;?','',css)
b64=lambda fn:base64.b64encode(open(fn,'rb').read()).decode()
AREAS=[json.load(open(f)) for f in sorted(glob.glob('areas/*/area.json'))]
def funn(n): return f" ({n} funn)" if n else ""
def build(A):
    D=f'{A}/data'; a=json.load(open(f'{A}/area.json')); M=json.load(open(f'{D}/model_out.json')); PNG=json.load(open(f'{D}/model_png.json'))
    for s,(h,f,w) in TXT.items():
        n=M['species'][s].get('n',0); note=a.get('notes',{}).get(s,'')
        if s!='alle' and 0<n<20: note=(note+' ' if note else '')+f'Bare {n} funn i utsnittet.'
        M['species'][s]['txt']=dict(h=h+(' '+note if note else ''),f=f,warn=bool(w))
    sp=M['species']; nrec=M['nrec']
    if nrec<200: intro=f"Bare {nrec} soppfunn er registrert i dette utsnittet, så de giftige artene kan godt finnes her selv om de ikke er meldt inn. "
    else: intro=""
    poison=(intro+f"Spiss giftslørsopp{funn(sp['giftslor']['n'])} vokser i samme fuktige granskog som traktkantarell. Hvit fluesopp{funn(sp['hvitflue']['n'])} står i sur gran- og bjørkeskog. "
            f"Flatklokkehatt{funn(M.get('n_flat',0))} vokser på stubber og ligner stubbeskjellsopp. Alle tre er dødelig giftige. Få kurven sjekket i soppkontrollen før du spiser noe du ikke er helt sikker på.")
    depth=a['path'].count('/')+1 if a['path'] else 0; up='../'*depth
    others=[f'<a href="{up}{o["path"]+"/" if o["path"] else ""}">{o["name"]}</a>' for o in AREAS if o['id']!=a['id']]
    nav=('Andre kart: '+', '.join(others)) if others else ''
    t=open('template.html').read()
    t=t.replace('/*__LEAFLET_CSS__*/',css).replace('/*__DATA__*/',json.dumps(M,ensure_ascii=False,separators=(',',':'))).replace('/*__PNG__*/',json.dumps(PNG,separators=(',',':')))
    t=t.replace('/*__GREY__*/',b64(f'{D}/base_grey.jpg')).replace('/*__SAT__*/',b64(f'{D}/base_sat.jpg'))
    for k,v in dict(title=a['title'],name=a['name'],road=a['road'],region=a['region'],s2_spring=a['s2_spring'],s2_late=a['s2_late'],gbif_date=a['gbif_date'],sat_label=a['sat_label'],poison_text=poison,nav=nav).items():
        t=t.replace('{{'+k+'}}',v)
    left=re.findall(r'\{\{\w+\}\}|/\*__\w+__\*/',t); assert not left,left
    out=os.path.join('site',a['path'],'index.html'); os.makedirs(os.path.dirname(out),exist_ok=True); open(out,'w').write(t)
    print(out,"MB",round(len(t.encode())/1e6,2),"| url( left in css:",css.count('url('))
for A in (sys.argv[1:] or [os.path.dirname(f) for f in sorted(glob.glob('areas/*/area.json'))]): build(A.rstrip('/'))
