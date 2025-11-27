"""Pulisce il dataset rimuovendo falsi positivi (es. investimenti finanziari)."""
from __future__ import annotations

import json
import logging
import pathlib
import re
import sys
from typing import Dict, List

CURRENT_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
SRC_DIR = ROOT_DIR / "src"

for path in (SRC_DIR, ROOT_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from incidenti_scraping.text_utils import normalize

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Pattern negativi: se presenti, l'articolo NON è un incidente stradale
NEGATIVE_PATTERNS = [
    r'\binvestiment[io]\s+(?:finanziari?|immobiliari?|pubblic[io]|privati?|europei?|nazionali?)',
    r'\binvestiment[io]\s+(?:in|per|da|di)\s+',
    r'\b(?:piano|programma|progetto)\s+di\s+investiment[io]',
    r'\b(?:milioni?|miliardi?)\s+(?:di\s+)?euro\s+(?:di\s+)?investiment[io]',
    r'\binvestiment[io]\s+(?:da|di)\s+\d+',
    r'\b(?:finanziamento|finanziare|finanziari?)\s+(?:pubblic[io]|privati?|europei?)',
    r'\b(?:borsa|mercato|azionari?|titoli?)\s+(?:di\s+)?investiment[io]',
    r'\b(?:fondo|fondi)\s+(?:di\s+)?investiment[io]',
    r'\b(?:rendimento|dividendo|capitale)\s+(?:di\s+)?investiment[io]',
    # Altri falsi positivi comuni
    r'\bincidente\s+(?:diplomatic[io]|politic[io]|amministrativ[io])',
    r'\b(?:investire|investito|investono)\s+(?:in|su|per)\s+(?:progetti?|infrastrutture|edilizia)',
    r'\b(?:investimento|investimenti)\s+(?:pubblic[io]|privati?)\s+(?:in|per|su)',
    # Violenza di genere e altri argomenti non correlati
    r'\b(?:violenza|maltrattamenti?)\s+(?:di\s+)?genere',
    r'\b(?:vittime?|percorso|assistenza)\s+(?:di\s+)?violenza',
    r'\b(?:centro|centri)\s+(?:antiviolenza|anti-violenza)',
    r'\b(?:codice\s+rosso)\s+(?:violenza|genere)',
    r'\b(?:giornata|giornata internazionale)\s+(?:per|contro)\s+(?:l\'?eliminazione\s+della\s+)?violenza',
    r'\b(?:percorso|percorsi)\s+(?:assistenzial[ie]|dedicat[io])\s+(?:alle\s+)?vittime',
    r'\b(?:violenza|abuso|maltrattamento)\s+(?:domestica|familiare|sulle\s+donne)',
    # Altri argomenti non correlati
    r'\b(?:basket|calcio|sport|partita|gara)\s+',
    r'\b(?:elezioni?|votazioni?|referendum|ballottaggio)',
    r'\b(?:festival|evento|manifestazione|sagra)',
    r'\b(?:progetto|progetti)\s+(?:ospedal[ie]|sanitari?|edilizi?)',
    # Lamentele residenti e problemi di traffico (non incidenti)
    r'\b(?:invivibile|insopportabile|esasperazione)\s+(?:per|a causa di|dovuto a)\s+(?:traffico|mezzi pesanti|rumore)',
    r'\b(?:residenti?|abitanti?)\s+(?:lamentano|scrivono|protestano|denunciano)',
    r'\b(?:tangenziale|strada)\s+(?:sotto casa|invivibile|insopportabile)',
    # Interventi preventivi e sicurezza stradale (non incidenti attuali)
    r'\b(?:interventi?|miglioramenti?|lavori?)\s+(?:sulla|sulle|per)\s+(?:segnaletica|sicurezza stradale|illuminazione)',
    r'\b(?:migliorare|miglioramento)\s+(?:la\s+)?sicurezza\s+stradale',
    r'\b(?:piano|piani)\s+(?:di|per)\s+(?:sicurezza|prevenzione)',
    # Truffe e reati (non incidenti)
    r'\b(?:si\s+finge|finge\s+di|fals[io])\s+(?:carabiniere|poliziotto|avvocato)',
    r'\b(?:truffa|truffatore|truffatric[ie]|estorcere|estorsione)',
    r'\b(?:presunti|falsi)\s+(?:incidenti?|sinistri?)\s+(?:che\s+coinvolgono|che\s+coinvolgerebbero)',
    # Rifiuti e ambiente (non incidenti)
    r'\b(?:rifiuti?|abbandono)\s+(?:sulle|sulla|sugli)\s+strade',
    r'\b(?:piano|piani)\s+(?:straordinari?|di\s+contrasto)\s+(?:all\'?|al)\s+abbandono',
    r'\b(?:citta\s+metropolitana|comune)\s+(?:contro|piano)\s+(?:rifiuti|abbandono)',
    # Processioni e eventi religiosi
    r'\b(?:busto|reliquie?|effigi?|simulacro|patrono)\s+(?:argenteo|sfilato|processione)',
    r'\b(?:processione|sfilata)\s+(?:religiosa|storica|tradizionale)',
    r'\b(?:festa|feste)\s+(?:patronale|religiosa)',
    # Articoli generali su vigili del fuoco (non incidenti specifici)
    r'\b(?:vigili\s+del\s+fuoco|vigile)\s+(?:in\s+prima\s+linea|attivita\s+di\s+soccorso|sempre\s+operativi)',
    r'\b(?:estate|periodo)\s+(?:di\s+fuoco|intensa\s+attivita)',
    r'\b(?:non\s+solo\s+fiamme|incendi\s+e\s+incidenti)\s+(?:ma|ma\s+anche)',
    # Interviste e opinioni su incidenti passati (non incidenti attuali)
    r'\b(?:contro|sdegno|ricordo|incubo)\s+(?:i\s+video|quello\s+che|quello\s+che\s+ho)',
    r'\b(?:video|foto)\s+(?:che\s+riprendono|del\s+dolore|condiviso)',
    r'\b(?:e\s+accaduto\s+anche\s+a\s+me|ho\s+vissuto|prov[ao]\s+sdegno)',
    r'\b(?:parlare|parla|intervista)\s+(?:e|di|su)\s+(?:un|una)\s+(?:ferit[io]|vittima)',
    # Articoli che parlano di incidenti in modo generico/riassuntivo
    r'\b(?:tra\s+incendi?|incidenti?\s+e\s+salvataggi?|incidenti?\s+in\s+generale)',
    r'\b(?:numerosi\s+gli\s+episodi|episodi\s+che\s+si\s+sono\s+verificati)',
    # Escludi se parla solo di sicurezza/prevenzione senza incidente specifico
    r'\b(?:sicurezza\s+stradale|prevenzione)\s+(?:senza|non)\s+(?:incidente|sinistro)',
    # Incidenti ferroviari (non stradali)
    r'\b(?:incidente|disastro|tragedia)\s+ferroviari[io]',
    r'\b(?:ferroviari[io]|treno|stazione)\s+(?:incidente|disastro|tragedia)',
    r'\b(?:tratta|linea)\s+(?:Corato|Andria|Bari).*?(?:incidente|disastro)',
    r'\b(?:Ferrotramviaria|stazione\s+centrale).*?(?:incidente|disastro)',
    # Commemorazioni e ricordi di incidenti passati
    r'\b(?:ricordo|memoria|anniversario|commemorazione)\s+(?:del|dell\'|dello|di)\s+(?:incidente|disastro|tragedia)',
    r'\b(?:corona\s+di\s+fiori|momento\s+di\s+raccoglimento)\s+(?:in\s+ricordo|per)',
    r'\b(?:nono|ottavo|settimo|sesto)\s+anniversario\s+(?:del|dell\'|dello)\s+(?:incidente|disastro)',
    r'\b(?:familiari\s+delle\s+vittime|vittime\s+del)\s+(?:incidente|disastro)',
    r'\b(?:fa\s+memoria|fare\s+memoria|custodia\s+della\s+memoria)',
    # Articoli pubblicitari e commerciali
    r'\b(?:noleggio|noleggiare)\s+(?:a\s+lungo\s+termine|auto|veicoli)',
    r'\b(?:migliori\s+offerte|offerte\s+di|soluzione\s+del\s+noleggio)',
    r'\b(?:alla\s+scoperta\s+delle|innovazione\s+tecnologica)\s+auto',
    r'\b(?:mercato\s+auto|autovetture|veicoli\s+moderni)\s+(?:smart|sicure)',
    r'\b(?:sistemi\s+di\s+infotainment|dispositivi\s+ADAS|assistenza\s+alla\s+guida)',
    r'\b(?:costo\s+fisso|bilancio.*?veicolo|mobilità\s+senza\s+pensieri)',
    # Sport e giochi (non incidenti)
    r'\b(?:Flying\s+Disc|squadra.*?qualificazione|serie\s+[ABC])\s+',
    r'\b(?:campionato\s+italiano|storica\s+qualificazione)',
    # Omicidi e reati (non incidenti stradali)
    r'\b(?:tentat[io]|tentato)\s+omicidi[io]',
    r'\b(?:omicidi[io]|agguato|in\s+carcere)\s+(?:in|a)',
    r'\b(?:ordinanza\s+di\s+custodia|indagat[ie]|procura)\s+',
    r'\b(?:marito\s+e\s+moglie|indagate.*?persone)',
    # Incidenti domestici (non stradali)
    r'\b(?:incidenti?\s+domestici?|ambiente\s+domestico)',
    r'\b(?:Istat.*?incidenti?\s+domestici?|dati\s+Istat.*?incidenti?)',
    # Morti per cause naturali/altre (non incidenti stradali)
    r'\b(?:Papa|Pontefice)\s+(?:Francesco|ha\s+lasciat[io]|funerali)',
    r'\b(?:corteo\s+funebre|spoglie\s+mortali|sepolt[io])\s+',
    r'\b(?:Santa\s+Maria\s+Maggiore|vescovo.*?dopo\s+la\s+morte)',
    # Scontri politici/elettorali (non incidenti stradali)
    r'\b(?:scontro|contesa)\s+(?:politic[io]|elettoral[ie]|campagna\s+elettorale)',
    r'\b(?:campagna\s+elettorale|manifesto\s+elettorale|consigliere\s+comunale)',
    r'\b(?:candidat[io]\s+(?:regionale|comunale)|gruppo\s+politico|Polis\s+contro)',
    # Rotatorie e interventi infrastrutturali (non incidenti)
    r'\b(?:nuova\s+rotatoria|rotatoria\s+sulla|realizzazione\s+di\s+una\s+rotatoria)',
    r'\b(?:Consiglio\s+Metropolitano|decreto\s+d\'urgenza|disciplinare\s+di\s+finanziamento)',
    r'\b(?:all\'incrocio.*?non\s+dove\s+si\s+verificano|dove\s+si\s+verificano\s+gli\s+incidenti)',
    # Regolamenti e ordinanze di viabilità (non incidenti)
    r'\b(?:nuovi\s+sensi\s+unici|divieti\s+di\s+fermata|variazioni\s+alla\s+viabilità)',
    r'\b(?:ordinanza.*?polizia\s+locale|comandante.*?polizia\s+locale.*?ordinanza)',
    r'\b(?:stalli\s+di\s+sosta|senso\s+unico\s+di\s+marcia|viabilità\s+cittadina)',
    # Eventi storici e commemorazioni storiche (non incidenti)
    r'\b(?:Disfida\s+di\s+Barletta|anni\s+dalla\s+Disfida|cavalieri\s+italiani)',
    r'\b(?:campo\s+di\s+battaglia|sfida\s+passata\s+alla\s+storia|evento\s+storico)',
    # Norme e regolamenti (non incidenti attuali)
    r'\b(?:norma\s+anti|piano\s+straordinario.*?gestione|contenimento.*?fauna)',
    r'\b(?:Coldiretti.*?strumento|approvata.*?norma|regolamento.*?approvato)',
    r'\b(?:emergenza.*?cinghiali|fauna\s+selvatica.*?Puglia)',
    # Spettacoli teatrali e culturali (non incidenti)
    r'\b(?:alunni.*?portano.*?teatro|spettacolo.*?teatro|messo\s+in\s+scena)',
    r'\b(?:Liceo.*?teatro|Antigone.*?Sofocle|teatro\s+comunale)',
    # Articoli su luoghi/edifici (non incidenti)
    r'\b(?:Masseria|masseria.*?resist.*?degrado|biciclette.*?bosco)',
    r'\b(?:gallerie.*?alberate|bosco.*?Scoparella|macchia\s+boschiva)',
    # Commemorazioni di persone (non incidenti attuali)
    r'\b(?:generosità.*?ricordo|ricordo\s+di.*?anni\s+fa|amici.*?colleghi.*?ricordare)',
    r'\b(?:sogni.*?irrimediabilmente\s+spezzati|perso\s+la\s+vita.*?anni\s+fa)',
    r'\b(?:donazione\s+degli\s+organi|hanno\s+vinto\s+tutti.*?piccoli\s+e\s+grandi)',
    # Test e verifiche strutturali (non incidenti)
    r'\b(?:test|verifica|verifiche)\s+(?:per|sulla|della)\s+(?:staticità|stabilità)',
    r'\b(?:staticità|stabilità)\s+(?:del|della|dello)\s+(?:cavalcavia|ponte|struttura)',
    r'\b(?:cavalcavia|ponte|struttura)\s+(?:della|del|dello)\s+(?:ex\s+\d+|strada)',
    r'\b(?:ingegner|esperto|dipartimento)\s+(?:.*?staticità|.*?verifica)',
    r'\b(?:relazione\s+sullo\s+stato|stato\s+effettivo)\s+(?:del|della|dello)\s+(?:cavalcavia|ponte)',
    # Gossip e cronaca rosa (non incidenti)
    r'\b(?:conquista|conquistato|conquista\s+un)\s+(?:calciatore|calciatrice)',
    r'\b(?:Grande\s+Fratello|reality|gossip)',
    r'\b(?:pizzicat[ao]|dolce\s+compagnia|affascinante)\s+(?:calciatore|calciatrice)',
    r'\b(?:serata\s+milanese|galeotta)',
    # Modifiche alla viabilità e ordinanze (non incidenti)
    r'\b(?:senso\s+unico|sensi\s+unici)\s+(?:per|di|sulla)\s+(?:via|strada)',
    r'\b(?:parte\s+(?:oggi|ufficialmente|ieri))\s+(?:il|la)\s+(?:senso\s+unico|sperimentazione)',
    r'\b(?:sperimentazione|ordinanza)\s+(?:che\s+vedrà|che\s+prevede)\s+(?:via|strada)',
    r'\b(?:modifica\s+dei\s+sensi\s+di\s+marcia|sensi\s+di\s+marcia)',
    r'\b(?:ordinanza.*?prevede.*?modifica|ordinanza.*?senso\s+unico)',
    r'\b(?:primo\s+giorno\s+con\s+il\s+senso\s+unico|scattata.*?ordinanza)',
    r'\b(?:percorribile\s+esclusivamente|direzione\s+che\s+conduce)',
    r'\b(?:intersezione\s+con\s+viale|variazioni\s+alla\s+segnaletica)',
    # Commemorazioni con borse di studio (non incidenti attuali)
    r'\b(?:borsa\s+di\s+studio|consegna.*?borsa)\s+(?:in\s+memoria|memoria\s+di)',
    r'\b(?:scomparsi|scompars[ao])\s+(?:in\s+un\s+incidente|in\s+un\s+sinistro)\s+(?:stradale\s+)?(?:nel|nel\s+\d{4})',
    r'\b(?:cerimonia\s+di\s+consegna|consegna.*?borsa)\s+(?:alla\s+studentes?|studente)',
    # Risse e violenze tra persone (non incidenti stradali)
    r'\b(?:rissa|risse)\s+(?:sullo|sulla|tra|tra\s+due)',
    r'\b(?:morso|morsi)\s+(?:stacca|staccato)\s+(?:il\s+)?lobo',
    r'\b(?:lobo\s+(?:sinistro|destro|dell\'orecchio))\s+(?:staccato|staccat[ao])',
    r'\b(?:contendenti?|rivale)\s+(?:con\s+il\s+lobo|violenta\s+rissa)',
    r'\b(?:scioccante\s+epilogo|violenta\s+rissa)',
    # Rifiuti abbandonati (non incidenti) - pattern più specifici
    r'\b(?:rifiuti\s+speciali|pneumatici\s+abbandonati|centinaia\s+di\s+pneumatici)',
    r'\b(?:abbandonat[io]\s+(?:in\s+fretta|di\s+notte|sulla|sulle))\s+(?:strade?|corato)',
    r'\b(?:pneumatici\s+usati|facilmente\s+recuperabili)',
    r'\b(?:testo\s+unico.*?materia\s+ambientale|Dlgs.*?n\.\s+\d+)',
    # Spettacoli teatrali e culturali (pattern più specifici)
    r'\b(?:Mistero\s+Buffo|Dario\s+Fo|giullare|teatro\s+medievale)',
    r'\b(?:arte\s+di\s+Fo|tradizione\s+istituzionale\s+del\s+teatro)',
    r'\b(?:joculatores|homo\s+ludens|homo\s+cogitans)',
    r'\b(?:commedia\s+dell\'arte|Eduardo\s+De\s+Filippo)',
    # Articoli di opinione e lettere (non incidenti)
    r'\b(?:Caro\s+professore|caro\s+professore|compito\s+di\s+classe)',
    r'\b(?:ventina\s+di\s+anni\s+fa.*?alunno|alunno.*?anni\s+fa)',
    r'\b(?:lettera|articolo\s+di\s+opinione|opinione)',
    # Incidenti ferroviari (pattern più specifici)
    r'\b(?:travolto|travolta)\s+(?:da\s+un\s+treno|da\s+un\s+convoglio)',
    r'\b(?:inseguit[ao]\s+sulle\s+rotaie|sulle\s+rotaie.*?inseguit[ao])',
    r'\b(?:finanziere|poliziotto|carabiniere)\s+(?:travolto|travolta)\s+(?:da\s+un\s+treno)',
    # Campagne elettorali e politica (pattern più specifici)
    r'\b(?:UDC|presenta.*?campagna\s+elettorale|campagna\s+di\s+comunicazione)',
    r'\b(?:candidato\s+(?:alla\s+)?(?:Provincia|Comune|Regione))',
    r'\b(?:marketing\s+elettorale|responsabile.*?marketing|portale.*?udc)',
    r'\b(?:sub\s+commissario\s+sezionale|tavolo\s+dei\s+relatori)',
    # Sport (pattern più specifici)
    r'\b(?:Basket.*?arriva|arriva.*?Massafra|lotteria\s+play-off)',
    r'\b(?:campionato.*?tregua|pausa\s+pasquale.*?campionato)',
    r'\b(?:Granoro\s+Corato|appuntamento\s+con\s+la\s+storia)',
    r'\b(?:visione\s+dei\s+film|pubblicità\s+concede\s+fiato)',
    # Articoli su eventi passati menzionati solo come contesto
    r'\b(?:ho\s+letto\s+della\s+morte|ho\s+letto.*?morte)\s+(?:di|del|della)',
    r'\b(?:nei\s+giorni\s+appena\s+trascorsi|giorni\s+appena\s+trascorsi)',
    r'\b(?:legittima\s+difesa|difesa\s+legittima)',
    r'\b(?:eventi\s+che\s+hanno\s+caratterizzato|caratterizzato.*?cronaca)',
    # Educazione stradale e progetti educativi (non incidenti)
    r'\b(?:a\s+lezione\s+di|lezione\s+di)\s+educazione\s+stradale',
    r'\b(?:educazione\s+stradale|sicurezza\s+stradale)\s+(?:nelle\s+scuole|scuola|progetto)',
    r'\b(?:progetto.*?educazione\s+stradale|capofila.*?progetto.*?scuole)',
    r'\b(?:scuola\s+media|scuole\s+(?:elementari|superiori))\s+.*?(?:educazione|sicurezza)\s+stradale',
    # Storie di bambini malati e diritti (non incidenti)
    r'\b(?:bambino\s+malato|bambini\s+malati|diritti\s+negati)',
    r'\b(?:storia\s+dolorosa|percorso\s+duro)\s+(?:di\s+un\s+bambino|bambino)',
    r'\b(?:padre.*?chiede.*?rispetto|sopravvivenza\s+del\s+bambino)',
    r'\b(?:momento\s+difficile.*?famiglia|diritti.*?bambino)',
    # Articoli sul Codice della Strada e norme (non incidenti)
    r'\b(?:nuovo\s+)?Codice\s+della\s+Strada|codice\s+della\s+strada',
    r'\b(?:legge.*?n\.\s*\d+.*?modificat[ao]|articoli.*?codice)',
    r'\b(?:Comandante.*?Vigili\s+Urbani|Vigili\s+Urbani.*?parla)',
    r'\b(?:confisca.*?motocicli|circolazione\s+di\s+motocicli)',
    r'\b(?:giro\s+di\s+vite.*?Ministero|Ministero.*?Interno.*?circolazione)',
    # Articoli su Chernobyl e eventi storici (non incidenti stradali)
    r'\b(?:ragazzi\s+di\s+Chernobyl|Chernobyl|centrale\s+nucleare\s+di\s+Chernobyl)',
    r'\b(?:orfani.*?Chernobyl|incidente.*?centrale\s+nucleare)',
    r'\b(?:catastrofico\s+incidente.*?1986|26\s+Aprile\s+1986)',
    r'\b(?:orfanotrofi.*?Russia|Kaluga|Veronish)',
    # Articoli sulla disoccupazione ed economia (non incidenti)
    r'\b(?:disoccupazione.*?città|disoccupazione\s+in\s+città)',
    r'\b(?:fotografia.*?situazione\s+economica|situazione\s+economica\s+coratina)',
    r'\b(?:sociologo.*?Palmisano|Assessore.*?Servizi\s+Sociali)',
    r'\b(?:bilancio\s+comunale|Camera\s+del\s+lavoro.*?CGIL)',
    r'\b(?:guadagna\s+meno\s+di.*?euro|coratino.*?guadagna)',
    # Commemorazioni di morti per infarto/cause naturali (non incidenti stradali)
    r'\b(?:in\s+memoria\s+del|ricordo\s+dell\')\s+(?:Senatore|Onorevole|Deputato)',
    r'\b(?:anniversario\s+della\s+scomparsa|scomparsa\s+del)',
    r'\b(?:stroncat[ao]\s+da\s+un\s+infarto|mort[ao]\s+per\s+infarto)',
    r'\b(?:infarto.*?anni|mort[ao].*?studio.*?Roma)',
    r'\b(?:lezioni\s+di\s+democrazia|azione\s+politica\s+e\s+parlamentare)',
    # Articoli su riqualificazione, lavori e aree pedonali (non incidenti)
    r'\b(?:area\s+pedonale|aree\s+pedonali)\s+(?:rialzat[ao]|restituisce)',
    r'\b(?:riqualificazione.*?piazza|lavori\s+di\s+riqualificazione)',
    r'\b(?:pedonalizzazione.*?piazza|piazza.*?pedonalizzazione)',
    r'\b(?:consiglieri\s+comunali.*?contestato|vespaio\s+di\s+polemiche)',
    r'\b(?:stravolgimento.*?piazza|funzione\s+di\s+luogo\s+del\s+passeggio)',
    r'\b(?:Caritas.*?area\s+pedonale|restituisce.*?piazza.*?funzione)',
    # Articoli che esplicitamente dicono "nessun incidente" o "tranquilla"
    r'\b(?:tranquill[ao]\s+(?:sulle\s+strade|dal\s+punto\s+di\s+vista))',
    r'\b(?:nessun\s+incidente|poche\s+code)',
    r'\b(?:pasquetta\s+tranquilla|tranquilla.*?strade)',
    r'\b(?:task-force.*?Polizia\s+Municipale|Polizia\s+Municipale.*?task-force)',
    r'\b(?:temperatura.*?rigida|veicoli.*?percorso.*?strade.*?campagna)',
    # COVID, tamponi e contagi (non incidenti stradali)
    r'\b(?:tamponi?|tampone)\s+(?:e\s+festività|nelle\s+farmacie|nei\s+centri\s+analisi)',
    r'\b(?:ondata\s+di\s+contagi|contagi.*?travolto|nuovi\s+positivi)',
    r'\b(?:terza\s+ondata|farmacie.*?centri\s+analisi)',
    r'\b(?:tamponi.*?molecolari|tamponi.*?antigenici)',
    r'\b(?:Asl.*?Comune.*?positivi|positivi.*?superato)',
    # Mercati finanziari, trading online e criptovalute (non incidenti)
    r'\b(?:borsa\s+e\s+investimenti|investimenti.*?mercati)',
    r'\b(?:mercati\s+finanziari|banche\s+centrali|inflazione)',
    r'\b(?:volatilità.*?mercati|risk\s+on|Banchieri\s+Centrali)',
    r'\b(?:mercato\s+criptovalutario|criptovalute|Bitcoin|Ethereum)',
    r'\b(?:monete\s+digitali|comparto.*?criptovalute)',
    r'\b(?:investimenti\s+online|trading\s+online|broker)',
    r'\b(?:strategie.*?investire|operare\s+sui\s+mercati)',
    r'\b(?:piattaforme.*?trading|piattaforme\s+internazionali)',
    r'\b(?:mercato\s+azionario|indici\s+azionari|rally\s+rialzista)',
    r'\b(?:correzione.*?mercato|terzo\s+trimestre.*?mercato)',
    r'\b(?:tendenza.*?caratterizzato.*?anno|binari\s+della\s+tendenza)',
    # Articoli storici sulla Resistenza e fascismo (non incidenti)
    r'\b(?:Donne\s+e\s+uomini.*?Resistenza|Resistenza.*?Corato)',
    r'\b(?:storia\s+cittadina.*?Resistenza|trilogia.*?fascismo)',
    r'\b(?:fascismo.*?città|Resistenza.*?storia)',
    r'\b(?:lotta.*?popolo\s+italiano|concittadini.*?Storia)',
    r'\b(?:ultimo\s+lavoro.*?storia|volume.*?Resistenza)',
    # "Travolto" usato in contesti non stradali (contagi, eventi)
    r'\b(?:ondata|contagi|eventi?)\s+(?:ha\s+travolto|hanno\s+travolto)',
    r'\b(?:travolto|travolta)\s+(?:le\s+festività|dalle\s+ondate|dai\s+contagi)',
    # Articoli storici su basi militari e guerra fredda (non incidenti)
    r'\b(?:pezzo\s+di\s+guerra\s+fredda|guerra\s+fredda.*?quadranti)',
    r'\b(?:base\s+missilistica|basi\s+missilistiche)',
    r'\b(?:Murgia\s+del\s+Ceraso|pedalate\s+murgiane)',
    r'\b(?:storia\s+contemporanea.*?base|protagonisti.*?storia\s+contemporanea)',
    r'\b(?:luoghi\s+strani.*?storia|destinati\s+all\'oblio.*?storia)',
    # Risse e liti con morsi (non incidenti stradali)
    r'\b(?:stacc[ao]\s+a\s+morsi|morsi.*?orecchio|morso.*?lobo)',
    r'\b(?:lite\s+(?:per|a\s+causa\s+di)\s+(?:un\s+)?parcheggio|parcheggio.*?lite)',
    r'\b(?:condannat[ao]\s+(?:a|alla)\s+(?:quasi\s+)?\d+\s+anni|pena.*?reclusione)',
    r'\b(?:rit[io]\s+abbreviato|gup\s+del\s+tribunale|tribunale\s+di\s+Trani)',
    r'\b(?:pena\s+complessiva.*?anni|condannat[ao].*?reclusione)',
    # Scontri verbali in consiglio comunale (non incidenti stradali)
    r'\b(?:scontro\s+in\s+consiglio|scontri\s+in\s+consiglio)',
    r'\b(?:scontro\s+verbale.*?consiglio|consiglio\s+comunale.*?scontro)',
    r'\b(?:presidente\s+del\s+consiglio\s+comunale|consigliere.*?consigliera)',
    r'\b(?:gestire.*?spegnere.*?scontro|stigmatizzare.*?parole.*?consigliere)',
    r'\b(?:ruolo\s+istituzionale.*?consiglio|prerogative.*?consiglio\s+comunale)',
    # Proteste per passaggi a livello chiusi (non incidenti)
    r'\b(?:ostaggi\s+del\s+passaggio\s+a\s+livello|passaggio\s+a\s+livello.*?chiuso)',
    r'\b(?:protesta.*?passaggio\s+a\s+livello|passaggio\s+a\s+livello.*?protesta)',
    r'\b(?:chiusura\s+prolungata.*?passaggio|passaggio.*?chiusura\s+prolungata)',
    r'\b(?:residenti.*?confinati.*?sbarre|sbarre.*?impossibilitati)',
    r'\b(?:disagi.*?passaggio\s+a\s+livello|passaggio.*?disagi)',
    r'\b(?:via\s+Bagnatoio.*?passaggio|passaggio.*?via\s+Bagnatoio)',
]

# Pattern positivi STRETTI: devono essere presenti per confermare che è un incidente stradale
# Richiediamo almeno UN indicatore di veicolo/strada E UN indicatore di incidente
VEHICLE_INDICATORS = [
    r'\b(?:auto|automobile|veicolo|macchina|vettura|motociclo|moto|bicicletta|bici|tir|camion|furgone|scooter)',
    r'\b(?:strada|via|piazza|strada provinciale|strada statale|sp\s*\d+|ss\s*\d+|ex\s*\d+)',
    r'\b(?:guid[ao]|conducent[ie]|autista|pilota)',
]

ACCIDENT_INDICATORS = [
    r'\b(?:incidente|sinistro|scontro|tamponamento|schianto|ribaltamento|collisione)',
    r'\b(?:travolto|investito|sbalzato|sbandato|perduto\s+il\s+controllo|uscito\s+di\s+strada)',
    r'\b(?:feriti?|mort[io]|decedut[io])\s+(?:nell\'?|nell[ao]|in\s+seguito\s+a\s+un\s+)?(?:incidente|sinistro|scontro)',
]


def is_road_accident(record: Dict) -> bool:
    """Verifica se un record è realmente un incidente stradale."""
    full_text = f"{record.get('title', '')} {record.get('excerpt', '')} {record.get('content', '')}"
    normalized = normalize(full_text)
    
    # Se contiene pattern negativi, escludilo
    for pattern in NEGATIVE_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            logger.debug("Escluso per pattern negativo: %s", record.get('title', '')[:60])
            return False
    
    # Escludi se esplicitamente dice "nessun incidente" o "tranquilla"
    no_accident_indicators = [
        r'\bnessun\s+incidente',
        r'\bnessun\s+sinistro',
        r'\btranquill[ao]\s+(?:sulle\s+strade|dal\s+punto\s+di\s+vista)',
        r'\b(?:giornata|giorno)\s+tranquill[ao]',
    ]
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in no_accident_indicators):
        logger.debug("Escluso: esplicitamente dice 'nessun incidente': %s", record.get('title', '')[:60])
        return False
    
    # Escludi se parla di incidenti solo in modo generico/riassuntivo
    # (es. "tra incendi e incidenti", "numerosi episodi di incidenti")
    generic_incident_patterns = [
        r'\b(?:tra|fra)\s+(?:incendi?|incidenti?|salvataggi?)\s+(?:e|ed)\s+(?:incidenti?|incendi?)',
        r'\b(?:numerosi|molti|diversi)\s+(?:gli\s+)?(?:episodi?|incidenti?)\s+(?:che\s+si\s+sono\s+verificati|avvenuti)',
        r'\b(?:incidenti?\s+in\s+generale|attivita\s+di\s+soccorso)',
    ]
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in generic_incident_patterns):
        # Ma solo se non descrive un incidente specifico
        specific_incident_indicators = [
            r'\b(?:si\s+e\s+verificat[io]|e\s+avvenut[io]|si\s+e\s+registrat[io])\s+(?:un|un\')?\s+incidente',
            r'\b(?:incidente|sinistro)\s+(?:che\s+si\s+e\s+verificat[io]|avvenut[io]|registrat[io])',
            r'\b(?:questa\s+mattina|questa\s+sera|oggi|ieri|poco\s+fa)\s+.*?\s+(?:incidente|sinistro)',
        ]
        if not any(re.search(pattern, normalized, re.IGNORECASE) for pattern in specific_incident_indicators):
            logger.debug("Escluso: menziona incidenti solo in modo generico: %s", record.get('title', '')[:60])
            return False
    
    # Escludi se parla di incidenti passati in modo troppo generico
    # (es. "l'ultimo incidente risale a tre settimane fa" senza descrivere l'incidente attuale)
    past_incident_only = re.search(
        r'\b(?:ultim[ao]|precedent[ie]|passat[ao])\s+incidente\s+(?:risale|e\s+risalito|avvenut[io])\s+(?:a|al|alla)',
        normalized,
        re.IGNORECASE
    )
    if past_incident_only:
        # Verifica se descrive anche un incidente attuale
        current_incident_indicators = [
            r'\b(?:si\s+e\s+verificat[io]|e\s+avvenut[io]|si\s+e\s+registrat[io])\s+(?:un|un\')?\s+incidente',
            r'\b(?:incidente|sinistro)\s+(?:che\s+si\s+e\s+verificat[io]|avvenut[io]|registrat[io])\s+(?:questa|oggi|ieri)',
            r'\b(?:questa\s+mattina|questa\s+sera|oggi|poco\s+fa)\s+.*?\s+(?:incidente|sinistro)',
        ]
        if not any(re.search(pattern, normalized, re.IGNORECASE) for pattern in current_incident_indicators):
            logger.debug("Escluso: parla solo di incidente passato: %s", record.get('title', '')[:60])
            return False
    
    # Escludi se menziona incidenti passati con date specifiche nel passato remoto
    # (es. "scomparsi in un incidente nel 1993" - commemorazione, non incidente attuale)
    past_incident_with_year = re.search(
        r'\b(?:scomparsi?|scompars[ao]|mort[io]|mort[ao]|decedut[io]|decedut[ao])\s+(?:in\s+un\s+)?(?:incidente|sinistro)\s+(?:stradale\s+)?(?:nel|nel\s+)(?:19|20)\d{2}',
        normalized,
        re.IGNORECASE
    )
    if past_incident_with_year:
        # Verifica se descrive anche un incidente attuale (non solo commemorazione)
        current_incident_indicators = [
            r'\b(?:si\s+e\s+verificat[io]|e\s+avvenut[io]|si\s+e\s+registrat[io])\s+(?:un|un\')?\s+incidente',
            r'\b(?:incidente|sinistro)\s+(?:che\s+si\s+e\s+verificat[io]|avvenut[io]|registrat[io])\s+(?:questa|oggi|ieri|poco\s+fa)',
            r'\b(?:questa\s+mattina|questa\s+sera|oggi|poco\s+fa|ieri)\s+.*?\s+(?:incidente|sinistro)',
            r'\b(?:incidente|sinistro)\s+(?:questa\s+mattina|questa\s+sera|oggi|poco\s+fa|ieri)',
        ]
        if not any(re.search(pattern, normalized, re.IGNORECASE) for pattern in current_incident_indicators):
            logger.debug("Escluso: menziona solo incidente passato con data: %s", record.get('title', '')[:60])
            return False
    
    # Escludi se parla solo di modifiche alla viabilità senza incidente specifico
    # (es. "senso unico per via X" senza menzionare un incidente)
    viabilita_patterns = [
        r'\b(?:senso\s+unico|sensi\s+unici|ordinanza.*?viabilità|modifica.*?sensi\s+di\s+marcia)',
        r'\b(?:sperimentazione|parte\s+(?:oggi|ufficialmente))\s+(?:il|la)\s+(?:senso\s+unico)',
    ]
    has_viabilita = any(re.search(pattern, normalized, re.IGNORECASE) for pattern in viabilita_patterns)
    
    if has_viabilita:
        # Verifica se descrive anche un incidente specifico (non solo ordinanza)
        specific_accident_indicators = [
            r'\b(?:si\s+e\s+verificat[io]|e\s+avvenut[io]|si\s+e\s+registrat[io])\s+(?:un|un\')?\s+incidente',
            r'\b(?:incidente|sinistro)\s+(?:che\s+si\s+e\s+verificat[io]|avvenut[io]|registrat[io])',
            r'\b(?:questa\s+mattina|questa\s+sera|oggi|poco\s+fa|ieri)\s+.*?\s+(?:incidente|sinistro)',
            r'\b(?:feriti?|mort[io]|decedut[io])\s+(?:in\s+seguito\s+a|nell\'?|nell[ao])\s+(?:un\s+)?(?:incidente|sinistro)',
            r'\b(?:scontro|tamponamento|schianto|ribaltamento|collisione)\s+(?:tra|fra|sulla|sulle)',
        ]
        if not any(re.search(pattern, normalized, re.IGNORECASE) for pattern in specific_accident_indicators):
            logger.debug("Escluso: parla solo di viabilità senza incidente: %s", record.get('title', '')[:60])
            return False
    
    # Deve contenere almeno UN indicatore di veicolo/strada E UN indicatore di incidente
    has_vehicle = any(
        re.search(pattern, normalized, re.IGNORECASE) for pattern in VEHICLE_INDICATORS
    )
    
    has_accident = any(
        re.search(pattern, normalized, re.IGNORECASE) for pattern in ACCIDENT_INDICATORS
    )
    
    if not (has_vehicle and has_accident):
        logger.debug(
            "Escluso: mancano indicatori (veicolo=%s, incidente=%s): %s",
            has_vehicle,
            has_accident,
            record.get('title', '')[:60],
        )
        return False
    
    return True


def clean_dataset(
    input_path: str | pathlib.Path,
    output_path: str | pathlib.Path | None = None,
    *,
    dry_run: bool = False,
) -> Dict:
    """Pulisce il dataset rimuovendo falsi positivi."""
    input_path = pathlib.Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"File non trovato: {input_path}")
    
    logger.info("=" * 80)
    logger.info("PULIZIA DATASET - REPORT DETTAGLIATO")
    logger.info("=" * 80)
    logger.info("Caricamento dataset da %s", input_path)
    with input_path.open("r", encoding="utf-8") as fh:
        records: List[Dict] = json.load(fh)
    
    logger.info("\n📊 STATISTICHE INIZIALI")
    logger.info("  Totale record prima della pulizia: %d", len(records))
    
    # Analisi per anno
    from collections import Counter
    years_before = Counter(r.get('year') for r in records if r.get('year'))
    logger.info("  Record per anno (prima):")
    for year in sorted(years_before.keys()):
        logger.info("    %s: %d record", year, years_before[year])
    
    cleaned = []
    removed = []
    removed_by_reason = {
        "pattern_negativo": [],
        "manca_veicolo": [],
        "manca_incidente": [],
    }
    
    logger.info("\n🔍 ANALISI RECORD...")
    for record in records:
        full_text = f"{record.get('title', '')} {record.get('excerpt', '')} {record.get('content', '')}"
        normalized = normalize(full_text)
        
        # Controlla pattern negativi
        excluded_by_negative = False
        for pattern in NEGATIVE_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                removed_by_reason["pattern_negativo"].append(record)
                excluded_by_negative = True
                break
        
        if excluded_by_negative:
            removed.append(record)
            continue
        
        # Controlla indicatori
        has_vehicle = any(
            re.search(pattern, normalized, re.IGNORECASE) for pattern in VEHICLE_INDICATORS
        )
        has_accident = any(
            re.search(pattern, normalized, re.IGNORECASE) for pattern in ACCIDENT_INDICATORS
        )
        
        if not has_vehicle:
            removed_by_reason["manca_veicolo"].append(record)
            removed.append(record)
        elif not has_accident:
            removed_by_reason["manca_incidente"].append(record)
            removed.append(record)
        else:
            cleaned.append(record)
    
    logger.info("\n✅ RISULTATI PULIZIA")
    logger.info("  Record mantenuti: %d (%.1f%%)", len(cleaned), (len(cleaned) / len(records) * 100) if records else 0)
    logger.info("  Record rimossi: %d (%.1f%%)", len(removed), (len(removed) / len(records) * 100) if records else 0)
    
    logger.info("\n📋 DETTAGLIO RIMOZIONI")
    logger.info("  Rimossi per pattern negativo: %d", len(removed_by_reason["pattern_negativo"]))
    logger.info("  Rimossi per mancanza indicatore veicolo: %d", len(removed_by_reason["manca_veicolo"]))
    logger.info("  Rimossi per mancanza indicatore incidente: %d", len(removed_by_reason["manca_incidente"]))
    
    # Analisi per anno dopo
    years_after = Counter(r.get('year') for r in cleaned if r.get('year'))
    logger.info("\n📅 DISTRIBUZIONE PER ANNO (DOPO)")
    for year in sorted(years_after.keys()):
        before_count = years_before.get(year, 0)
        after_count = years_after[year]
        removed_count = before_count - after_count
        logger.info("    %s: %d → %d (rimossi: %d)", year, before_count, after_count, removed_count)
    
    if removed:
        logger.info("\n🗑️  ESEMPI DI RECORD RIMOSSI (primi 10):")
        for i, r in enumerate(removed[:10], 1):
            logger.info("  %d. [ID: %s] %s", i, r.get('id', 'n/a'), r.get('title', 'n/a')[:80])
    
    if dry_run:
        logger.info("\n⚠️  DRY RUN: nessun file modificato")
        return {
            "total": len(records),
            "kept": len(cleaned),
            "removed": len(removed),
            "removed_by_reason": {k: len(v) for k, v in removed_by_reason.items()},
            "years_before": dict(years_before),
            "years_after": dict(years_after),
            "removed_samples": [{"id": r.get('id'), "title": r.get('title', '')[:80]} for r in removed[:10]],
        }
    
    # Salva il dataset pulito
    if output_path is None:
        output_path = input_path
    
    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(cleaned, fh, ensure_ascii=False, indent=2)
    
    # Salva anche i record rimossi per la dashboard
    removed_path = output_path.parent / f"{output_path.stem}_removed.json"
    with removed_path.open("w", encoding="utf-8") as fh:
        json.dump(removed, fh, ensure_ascii=False, indent=2)
    
    logger.info("\n💾 Dataset pulito salvato in %s", output_path)
    logger.info("💾 Record rimossi salvati in %s", removed_path)
    logger.info("=" * 80)
    
    return {
        "total": len(records),
        "kept": len(cleaned),
        "removed": len(removed),
        "removed_by_reason": {k: len(v) for k, v in removed_by_reason.items()},
        "years_before": dict(years_before),
        "years_after": dict(years_after),
        "output": str(output_path),
    }


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description="Pulisce il dataset da falsi positivi")
    parser.add_argument(
        "--input",
        default="data/incidents.json",
        help="File JSON di input",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="File JSON di output (default: sovrascrive input)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra statistiche senza modificare file",
    )
    parser.add_argument(
        "--dashboard-data",
        default="dashboard/public/data/incidents.json",
        help="Copia anche nella cartella dashboard",
    )
    args = parser.parse_args()
    
    result = clean_dataset(
        args.input,
        args.output,
        dry_run=args.dry_run,
    )
    
    if not args.dry_run:
        # Copia anche nella cartella dashboard se specificato
        if args.dashboard_data:
            dashboard_path = pathlib.Path(args.dashboard_data)
            dashboard_path.parent.mkdir(parents=True, exist_ok=True)
            with pathlib.Path(result["output"]).open("r", encoding="utf-8") as src:
                data = json.load(src)
            with dashboard_path.open("w", encoding="utf-8") as dst:
                json.dump(data, dst, ensure_ascii=False, indent=2)
            logger.info("Dataset copiato anche in %s", dashboard_path)
            
            # Copia anche i record rimossi
            removed_path = pathlib.Path(result["output"]).parent / f"{pathlib.Path(result['output']).stem}_removed.json"
            if removed_path.exists():
                dashboard_removed_path = dashboard_path.parent / f"{dashboard_path.stem}_removed.json"
                with removed_path.open("r", encoding="utf-8") as src:
                    removed_data = json.load(src)
                with dashboard_removed_path.open("w", encoding="utf-8") as dst:
                    json.dump(removed_data, dst, ensure_ascii=False, indent=2)
                logger.info("Record rimossi copiati anche in %s", dashboard_removed_path)


if __name__ == "__main__":
    main()

