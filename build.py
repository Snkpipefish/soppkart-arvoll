import json, re, base64, os
D=json.load(open('data/model_out.json')); PNG=json.load(open('data/model_png.json'))
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
 "trompet":("Rik løvskog med hassel og eik på kalkrik grunn. Sjelden her, fordi berggrunnen i åsene er sur. Bare ti funn i området.","Ingen giftige forvekslingsarter.",0),
 "sandsopp":("Tørr furuskog på koller og grunnlendte rygger.","Middelmådig matsopp, men uten giftige forvekslingsarter.",0),
 "blodror":("Sur granskog og blandingsskog. Mørkebrun hatt, røde rørmunninger og kjøtt som blåner kraftig.","Må varmebehandles godt. Kan forveksles med andre rørsopper med røde rørmunninger. Bare for sikre plukkere.",1),
 "giftslor":("Fuktig, mosegrodd granskog, de samme stedene som traktkantarell. Kartet viser hvor du bør være ekstra nøye med kurven.","Dødelig giftig. Skader nyrene, og symptomene kommer først etter 2 til 14 dager.",1),
 "hvitflue":("Sur gran- og blandingsskog med bjørk. Helt hvit sopp med ring, og knoll i en pose nederst på stilken.","Dødelig giftig. Forveksles med sjampinjonger og andre hvite skivesopper. Grav alltid opp hele stilken på hvite sopper.",1)}
for s,(h,f,w) in TXT.items(): D['species'][s]['txt']=dict(h=h,f=f,warn=bool(w))
css=open('data/leaflet.css').read(); css=re.sub(r'[^{};]*url\([^)]*\)[^;}]*;?','',css)
b64=lambda fn:base64.b64encode(open(fn,'rb').read()).decode()
t=open('template.html').read()
t=t.replace('/*__LEAFLET_CSS__*/',css).replace('/*__DATA__*/',json.dumps(D,ensure_ascii=False,separators=(',',':'))).replace('/*__PNG__*/',json.dumps(PNG,separators=(',',':')))
t=t.replace('/*__GREY__*/',b64('data/base_grey.jpg')).replace('/*__SAT__*/',b64('data/base_sat.jpg'))
os.makedirs('site',exist_ok=True); open('site/index.html','w').write(t)
print("html MB",round(len(t.encode())/1e6,2),"| url( left in css:",css.count('url('))
