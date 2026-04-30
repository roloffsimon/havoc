# Generator-Wortlisten — deutsche Adaption

**Zweck:** Erste Vorschlagsspalte für die Übersetzung/Adaption der 248 Tokens
aus `backend/app/stanza.py`, die das kombinatorische Material für *Sea and
Spar Between* (Montfort/Strickland 2010) bilden. Eine deutsche Fassung der
Website soll bei aktivem `lang=de`-Toggle diese Listen statt der englischen
verwenden.

**Update 2026-04-30:** Jede Tabelle wurde um die Spalte
*„DE-Vorschlag (Kontext)"* erweitert. Diese Vorschläge berücksichtigen den
Verwendungskontext des englischen Ausdrucks bei Melville bzw. Dickinson —
gestützt auf eine Volltextrecherche in den vorliegenden EPUB-Ausgaben
(Penguin *Moby-Dick* 2009; Project-Gutenberg *Poems by Emily Dickinson,
Three Series, Complete*; *Poems: First/Second Series*). Wo die ursprüngliche
Vorschlagsspalte den Kontext bereits trifft, wird sie übernommen; wo der
Beleg eine andere Wortwahl nahelegt, ist ein Wechsel mit kurzer Begründung
und Quellenangabe (Kapitel- oder Gedichtanfang) eingetragen.

**Politischer Lesehorizont des Projekts.** Da das Werk Ressourcenausbeutung
zum Thema hat, sind diejenigen Tokens besonders aufgeladen, die bei Melville
das juristisch-ökonomische Aneignungslexikon tragen — vor allem in Kap. 36
(Doublonen-Szene: das Goldstück als an den Mast genagelte Wertfetisch), Kap.
37 (Ahabs *„Swerve me?"*-Monolog: das kapitalistische Subjekt, das nicht
abgelenkt werden kann) und Kap. 89 (*Fast-Fish/Loose-Fish*: das Walfangrecht
als Modell des Imperialismus, der Sklaverei und der Aneignung „herrenloser"
Güter). Die Übersetzungs­vorschläge in den entsprechenden Zeilen sind so
gewählt, daß sie diese politische Dimension hörbar halten. *Loose-Fish*
wird zu **freier Fisch** (statt Rathjens *loser Fisch*), weil *frei* im
Deutschen die juristische Konnotation trägt, die *los* fehlt — vgl.
*Freiwild*, *vogelfrei*, *zur freien Verfügung*, *Freibeuterei*. Auch in
Liste 4b (MELVILLE_SYLLABLE) und Liste 8 (NAILED_ENDING) sind die
Industrie-Material-Topik und die Insignien der Befehlsgewalt entsprechend
geschärft. Bei Dickinson ist das politische Vokabular leiser, aber präsent
— in den *Mine-Gedichten*, in *Repeal*, *Possession*, *Tenant*, *Property*.

**Quellenlage der Vorschläge:**
- *Moby-Dick*-Termini orientieren sich tendenziell an **Friedhelm Rathjen**
  (2004, Zweitausendeins) — philologisch näher am Original als Jendis.
  Wo Jendis (2001) populärer ist, vermerkt.
  
- *Dickinson*-Anklänge orientieren sich tendenziell an **Gunhild Kübler**
  (Hanser, *Sämtliche Gedichte*, 2015), gelegentlich an **Paul Celan**
  (Auswahl) und **Werner von Koppenfels**.
  
- "(eigen)" = freier Vorschlag ohne Vorbild in einer kanonischen Übersetzung.

**Strukturelle Probleme**, die in den Anmerkungen mitlaufen:
1. **Silbenzahl** — die Listen sind nach Silben gestaffelt; deutsche
   Äquivalente sind oft länger (`eternity` 4 → *Ewigkeit* 3, aber
   `immortality` 5 → *Unsterblichkeit* 4).
2. **Genus** — `_one_noun` reiht "one X one Y…"; im Deutschen müsste
   *ein/eine/ein* mitwandern oder ganz wegfallen (Vorschlag: weglassen).
3. **`-less`-Suffix** — Dickinsons produktivstes Suffix; *-los* funktioniert
   bei manchen, bei anderen (besonders deverbalen Bildungen wie
   *efface-less*, *perturb-less*) gar nicht. Hier müsste der Generator
   `_rise_and_go` / `_but` ggf. neu gedacht werden.
4. **Komposita** — `_compound_course` baut englisch-fremde Komposita
   (*"bag-fin course"*); im Deutschen sind Komposita normal und
   verlieren genau diese Verfremdung.

**Update 2026-04-30 (Generator-Implementation).** Während der Umsetzung
in [`backend/app/stanza_de.py`](../../backend/app/stanza_de.py) ergaben
sich an einigen Stellen Anpassungen gegenüber der Spalte
„DE-Vorschlag (Kontext)", überwiegend aufgrund kombinatorischer
Notwendigkeiten:
- **Kasus-Stammform im Kompositum**: N-Deklinationen und Pluralia
  müssen im Erstglied eines Kompositums in der obliquen Stammform
  (mit Fugen-n) stehen — *Falke* → *Falken-* (vgl. *Falkenauge*),
  *Hexe* → *Hexen-* (*Hexenkessel*), ebenso *Bienen-, Pritschen-,
  Flossen-, Hauben-, Hülsen-, Scheiben-, Lumpen-, Narren-*. Zu starke
  Apokopen (*Bien, Hex, Hak*) wurden gleichzeitig korrigiert.
- **Genus-bewusste Artikel** in `_one_noun`, `_but`, `_nailed`:
  Einträge werden als Tupel `(Artikel, Substantiv)` geführt, damit
  der korrekte Artikel pro Genus (bzw. Kasus) verkettet werden kann.
- **Zirkumposition** in `_compound_course`: `COURSE_START` wird als
  `(Präfix, Suffix)` geführt (z. B. `('auf den ', ' versessen')`),
  weil das deutsche Kompositum in den Slot zwischen Präfix und
  Suffix einrückt.
- **Kollisionsauflösung** bei Doppelungen, die aus der
  Kontext-Spalte herrühren (`retrieve`/`retriever`).

Diese Anpassungen sind in der jeweils letzten Spalte der Tabellen
unter „Generator-Form" dokumentiert. Wo die Generator-Form leer ist,
wird die Spalte „DE-Vorschlag (Kontext)" 1:1 verwendet.

---

## 1. SHORT_PHRASE (19) — kurze Imperative/Anrufe

| EN | Silben | DE-Vorschlag | Silben | DE-Vorschlag (Kontext) | Kontext-Beleg |
|---|---|---|---|---|---|
| circle on | 3 | kreise nur | 3 | kreise weiter | M: Ixion-Stelle ("slowly wheeling circle, like another Ixion I did revolve") — die Drehbewegung der kapitalistischen Akkumulation als mythische Endlosschleife (Ixion am Rad: ewige Strafe als Bild der Selbst-Reproduktion des Antriebs). |
| dash on | 2 | stürme nur | 3 | voran nun | M Kap. 134: Ahabs Schluß-Befehl an die Ruderer ("Dash on, my men! Will ye not save my ship?"). Imperativ-Form der Treibjagd; *voran* (militärisch-extraktiv) hält den Befehlston der Walfang-Industrie, in dem Mannschaft und Beute denselben Antriebsbefehlen folgen. |
| let them | 2 | lass sie | 2 | lass sie | M Kap. 11: "Let them talk of their oriental summer climes of everlasting conservatories" — Ishmaels Trotz gegen die Komfort-Topik der Plantagen-/Kolonial-Ökonomie (orientalische Sommer = Bezug auf Karibik-/Südsee-Tropenökonomien). *Lass sie* hält die kontemptive Geste gegen die bürgerliche Ferne-Phantasie. |
| listen now | 3 | horche jetzt | 3 | horch nun | D häufige Hör-Anrufung; *horch* poetisch markierter als *horche* |
| loop on | 2 | schling fort | 4 | windet euch | (eigen) — wenn paratactisch zu *circle/wheel/whirl*, ist die Schlingen-/Schleifen-Bewegung gemeint |
| oh time | 2 | o Zeit | 2 | o Zeit | D-Anrufungston bestätigt (Kübler) |
| plunge on | 2 | stürz fort | 3 | hinab nun | M: das Pequod-Stürzen ins Wasser ("plunge"); *hinab* trifft die Vertikale |
| reel on | 2 | spul fort | 3 | taumle nur | D: "Inebriate of air am I... Reeling, through endless summer days" — der Rausch-Taumel, nicht das technische Spulen |
| roll on | 2 | roll fort | 3 | rolle nur | M Kap. 35: Byron-Zitat aus *Childe Harold's Pilgrimage* IV.179 ("Roll on, thou deep and dark blue ocean, roll!") — Byrons Apostrophe an die Indifferenz des Ozeans gegenüber den Ruinen menschlicher Imperien. Im Werk-Kontext: das Meer als das, was die kapitalistische Akkumulation überdauert und überschwemmt. *rolle nur* hält die zynische Gleichmut-Geste. |
| run on | 2 | renn fort | 3 | jag nur | M Kap. 35: "his mad mind would run on in a breathless race" — Ahabs Monomanie als kapitalistische Rationalität, die im atemlosen Vorwärts ihre eigene Vernichtung produziert. *jag nur* trägt zugleich das Hetz-Verhältnis zur Beute (Walfang) und das Selbst-Hetz-Verhältnis Ahabs. |
| spool on | 2 | spul fort | 3 | spinn weiter | M Kap. 60: Walfangleine läuft durch die Nut — *spinn* erinnert an *spun*/Garn und löst Kollision mit *reel on* |
| steady | 2 | stetig | 2 | stetig | M nautisch ("heave to... to steady"); D: "Till sundown crept, a steady tide" — Doppelung Befehl/Gleichmaß |
| swerve me? | 2 | mich beugen? | 3 | mich aufhalten? | M Kap. 37, Ahab-Monolog ("Swerve me? ye cannot swerve me, else ye swerve yourselves! man has ye there. ... The path to my fixed purpose is laid with iron rails"). Das kapitalistische Subjekt, das nicht abgelenkt werden kann; *aufhalten* trägt zugleich physisches Hindern und ökonomisches Festhalten/Hemmen — die zentrale Geste, die Ahab seinen Verfolgern abspricht. Rathjen: *abbringen*; *beirren* zu kognitiv. |
| turn on | 2 | dreh fort | 3 | wend dich | M häufig im Kreuzkurs-Idiom ("turn and tack"); *wend* nautisch genauer |
| wheel on | 2 | kreise fort | 3 | kreis nur | M Ixion-Stelle (s. *circle on*) — *kreis nur* hält die Silbe und korrespondiert lautlich mit *circle on* |
| whirl on | 2 | wirbel fort | 4 | wirble nur | (eigen) — *wirble* dreisilbig, näher an Original-Silbenzahl |
| you -- too -- | 2 | du -- auch -- | 2 | du -- auch -- | D: typische Apostrophe (Kübler-Konvention bestätigt) |
| fast-fish | 2 | fester Fisch | 3 | fester Fisch | M Kap. 89: "A Fast-Fish belongs to the party fast to it" — die erste Maxime des Walfangrechts, von Melville ironisch als Modell allen Eigentumsrechts ausgestellt. *Fest* trägt im Deutschen das Festgemachte/Festgehaltene und korrespondiert mit *Festhalten*, *Festsetzen*. Rathjen-Tradition. |
| loose-fish | 2 | loser Fisch | 3 | loser Fisch | M Kap. 89: "a Loose-Fish is fair game for anybody who can soonest catch it" — Melvilles Pointe entfaltet sich politisch: "What was America in 1492 but a Loose-Fish... What was Poland to the Czar? What Greece to the Turk? What India to England? What at last will Mexico be to the United States? All Loose-Fish." *Frei* trägt im Deutschen das juristische Aneignungs-Moment (vgl. *Freiwild*, *vogelfrei*, *Freibeuterei*), das *los* nicht hat. Pointiert die Schluß-Apostrophe: "And what are you, reader, but a Loose-Fish and a Fast-Fish, too?" → *„Und was sind Sie, Leser, anders als ein freier Fisch und ein fester Fisch zugleich?"* — die Paradoxie zwischen Subjektivität und Verfügbarkeit hörbar. (Jendis: *loser Fisch*; hier bewußte Abweichung mit Rücksicht auf den politischen Lesehorizont.) |

---

## 2. DICKINSON_NOUN — gestaffelt nach Silbenzahl

### 2a) 1-silbig (44) — gespeist in `_one_noun` ("one X one Y one Z one W")

> **Hinweis:** Im Deutschen müsste der Artikel mitlaufen, was Genus-Probleme
> erzeugt. Vorschlag: Artikel weglassen, ggf. Bindestrich-Konstruktion
> (*"Luft Kunst Sorge Tür"* oder *"Luft – Kunst – Sorg – Tür"*).
> Generator-Funktion `_one_noun` müsste angepasst werden.
>
> **Generator-Lösung:** Jeder Eintrag wird im Code als Tupel
> `(Artikel, Wort)` geführt; die Funktion `_one_noun` rendert pro Slot
> Artikel + Wort, getrennt durch Em-Dash (Dickinson-Schriftbild). Für
> die zwei artikellosen Sonderfälle (*je* distributiv, *hell* adjektivisch)
> ist der Artikel `None` und das Wort steht ohne Artikel.

| EN | DE-Vorschlag | Silben (DE) | Genus | DE-Vorschlag (Kontext) | Generator-Form | Kontext-Beleg |
|---|---|---|---|---|---|---|
| air | Luft | 1 | f | Luft | eine Luft | D "Inebriate of air am I" — *Luft* trägt das Trunkenheitsmotiv |
| art | Kunst | 1 | f | Kunst | eine Kunst | D "Have I the art to say" — *Kunst* als Vermögen/Können, beibehalten |
| care | Sorg | 1 | f | Sorg | eine Sorg | D "wonder we could care / For that old faded midnight"; M "carking cares of earth" — *Sorg* (Kübler) trifft beides |
| door | Tür | 1 | f | Tür | eine Tür | D "The opening of a door" (Suspense), "When winter shakes the door" — Schwellen-Topos |
| dust | Staub | 1 | m | Staub | ein Staub | D "his frame was dust" — biblisches *Staub* |
| each | jed | 1 | – | je | je *(artikellos)* | (eigen) — *je* einsilbig, distributiv; D "put them each in separate drawers" |
| ear | Ohr | 1 | n | Ohr | ein Ohr | D "an ear which had its own tenacious fastidiousness", "On whose forbidden ear" — bewusst gewähltes Sinnesorgan |
| earth | Erd | 1 | f | Erd | eine Erd | D "earth seems so / To those in heaven now"; M "carking cares of earth" — *Erd* (Kübler-Apokope) |
| fair | schön | 1 | adj | hell | hell *(artikellos)* | (eigen) — D "Too fair / For credibility's temerity"; *hell* fasst die Lichtkomponente, ohne *schön* zu reduplizieren |
| faith | Glaub | 1 | m | Glaub | ein Glaub | D "Read then of faith / That shone above the fagot" — märtyrerischer *Glaub* |
| fear | Furcht | 1 | f | Furcht | eine Furcht | D "I fear a thing / That comprehendeth me" — *Furcht* (vor dem Allumfassenden) |
| friend | Freund | 1 | m | Freund | ein Freund | D "If in that room a friend await / Felicity or doom" — Freund/Verhängnis-Konstellation |
| gold | Gold | 1 | n | Gold | ein Gold | D: "the gold / In using wore away" — Abnutzung des Edelmetalls durch Gebrauch (klassische Marx'sche Geld-Theorie *avant la lettre*). M Kap. 36: die Doublone als an den Mast genagelte Wertfetisch-Münze; "the gold cup of sperm oil" — explizite Gleichsetzung von Wal-Substanz und Gold. *Gold* unverzichtbar. |
| grace | Huld | 1 | f | Huld | eine Huld | D "That new grace / Glow plain and foreign" — religiöse *Huld* gegen *Gnade* (2 Silben) |
| grass | Gras | 1 | n | Gras | ein Gras | D Gedicht IX "THE GRASS. The grass so little has to do" — Hauptmotiv |
| grave | Grab | 1 | n | Grab | ein Grab | D "The grave would hinder me"; "by the grave's repeal" — *Grab* trifft die Schwelle |
| hand | Hand | 1 | f | Hand | eine Hand | D "the wind... working like a hand / Whose fingers brush the sky" |
| hill | Höh | 1 | f | Höh | eine Höh | D "The red upon the hill" — *Höh* (Kübler-Apokope) hält Silbe; M "hill-side blue" |
| house | Haus | 1 | n | Haus | ein Haus | D "The bustle in a house / The morning after death" |
| joy | Freud | 1 | f | Freud | eine Freud | D "'T is so much joy! 'T is so much joy!" — Wiederholungsfigur; *Freud* (Kübler-Tradition) |
| keep | Hut | 1 | f | Hut | eine Hut | M "Keep him nailed" (= überwachen); *Hut* deckt Verwahrung/Wache |
| leg | Bein | 1 | n | Bein | ein Bein | M Ahabs Holzbein, Hauptmotiv |
| might | Macht | 1 | f | Macht | eine Macht | M: "the now tested reality of his might had in former legendary times" — Ahabs *might* als geprüfte Realität, deren Mythos sich bewährt; *Macht* trägt den ganzen Bedeutungsraum der politischen Gewalt (Großmacht, Kolonialmacht, Machtanspruch), der bei Melville mitschwingt. |
| mind | Geist | 1 | m | Sinn | ein Sinn | (Wechsel zur Vermeidung der Kollision mit *thought*) — D "the writer's own mind"; M "his mad mind would run on" — *Sinn* hier offener |
| morn | Früh | 1 | f | Früh | eine Früh | D "Merry that it is morn"; M "the clearness of the morn" — *Früh* (Kübler-Apokope) bewahrt Silbe |
| name | Nam | 1 | m | Nam | ein Nam | D "Brave names of men", "Though my name / Rang loudest" — *Nam* (poet. Apokope) |
| need | Not | 1 | f | Not | eine Not | D "Requires sorest need"; M "if need should be" — *Not* trifft Existenznotwendigkeit |
| noon | Mittag | 2 | m | Mittag | ein Mittag | D "Her public is the noon"; M "ere noon the dead whale was brought" — Silbenverlust hinzunehmen, *Mittag* unverzichtbar |
| pain | Pein | 1 | f | Pein | eine Pein | D Gedicht "MYSTERY OF PAIN. Pain has an element of blank"; "periods of pain" — *Pein* hält Silbe und Klang |
| place | Ort | 1 | m | Ort | ein Ort | M "to take the place of Ahab's bowsman" — *Ort* als Stelle/Position |
| play | Spiel | 1 | n | Spiel | ein Spiel | D "New children play upon the green" — *Spiel* trägt Kindheits-/Theater-Doppelheit |
| rest | Ruh | 1 | f | Ruh | eine Ruh | D "And angels know the rest" — *Ruh* (Kübler-Apokope); Doppelsinn Rest/Ruhe |
| rose | Ros | 1 | f | Ros | eine Ros | D "She rose to his requirement" + Rosen-Topos; *Ros* (Kübler-Apokope, Goethe-Echo) |
| show | Schau | 1 | f | Schau | eine Schau | D "is there nothing else / That we can show to-day?" — *Schau* (Aus-/Vorzeigen) |
| sight | Sicht | 1 | f | Blick | ein Blick *(m, korrigiert)* | (Wechsel) — D "you saturated sight, / And I had no more eyes"; M "in full sight of it" — *Blick* trifft das Augenmoment präziser als *Sicht* |
| sky | Blau | 1 | n | Blau | ein Blau | D "Whose fingers brush the sky"; "the brain is wider than the sky" — *Blau* (Celan-Anklang) hält Silbe und korrespondiert mit M "hill-side blue" |
| snow | Schnee | 1 | m | Schnee | ein Schnee | D "uniforms of snow", "the punctual snow" |
| star | Stern | 1 | m | Stern | ein Stern | D "Here a star, and there a star, / Some lose their way" |
| thought | Sinn | 1 | m | Gedank (2) | ein Gedanke *(Vollform; entkollidiert mit mind→Sinn)* | (eigen) — D "without the thought of publication"; M "one painful thought connected with the tale"; *Denk* (Apokope) entkollidiert mit *mind* |
| tree | Baum | 1 | m | Baum | ein Baum | D "A drop fell on the apple tree"; M "this pine-tree shakes down its sighs" |
| well | Quell | 1 | m | Quell | ein Quell | (eigen) — *Quell* trägt poetischen Topos der Tiefe und Lebendigkeit |
| wind | Wind | 1 | m | Wind | ein Wind | M "Euroclydon: The northeast wind"; D "I'd wind the months in balls" |
| world | Welt | 1 | f | Welt | eine Welt | M / D häufig — "remotest nooks" der Welt |
| year | Jahr | 1 | n | Jahr | ein Jahr | D "If I could see you in a year" |

### 2b) 2-silbig (21)

| EN | DE-Vorschlag | Silben (DE) | DE-Vorschlag (Kontext) | Kontext-Beleg |
|---|---|---|---|---|
| again | wieder | 2 | wieder | D häufig — "And signed the fete away. / ...returns again" |
| alone | allein | 2 | allein | D "And leave the soul alone"; M Job-Motto "I only am escaped alone" |
| better | besser | 2 | besser | (philologisch unauffällig) |
| beyond | jenseits | 2 | jenseits | M "beyond the art of man"; D "beyond the doorstep" — *jenseits* trifft topographisch und metaphysisch |
| delight | Wonne | 2 | Wonne | D "Say quick, that I may dower thee / With last delight I own"; M "delight, top-gallant delight" — *Wonne* (Kübler) hält den exaltierten Ton |
| dying | Sterben | 2 | Sterben | D "the defeated, dying"; M "no dying Chaldee" — Verbalsubstantiv hält den Prozess |
| easy | einfach | 1 | leichthin | (eigen, 2 Silben) — D "Old-fashioned eyes, / Not easy to surprise"; M "easy, rollicking freedom"; *leichthin* trifft Adverb-Sinn |
| enough | genug | 2 | genug | M "gullible enough"; D "small enough to appear as dots" |
| ever | immer | 2 | immer | M "ever contracting towards the button-like black bubble"; D "Nor ever guessed" |
| father | Vater | 2 | Vater | D "her father's grounds"; M Captain Sleet's father |
| flower | Blume | 2 | Blume | D "WITH A FLOWER. I hide myself within my flower"; M "as well as the flower, his glance awaits the dawn" |
| further | weiter | 2 | ferner | (eigen) — D "And the children no further question"; M "further blows from him" — *ferner* zwischen räumlich und temporal |
| himself | er selbst | 2 | er selbst | D "But only to himself is known"; M Melville über sich selbst |
| human | menschlich | 2 | menschlich | M "They are never quite human"; D "Next to the robin / In every human soul" |
| morning | Morgen | 2 | Morgen | D "Our share of morning"; D "Two swimmers wrestled on the spar / Until the morning sun" |
| myself | ich selbst | 2 | ich selbst | D "For myself, although I had corresponded with her"; M Ishmaels Selbstanrede |
| power | Stärke | 2 | Gewalt | M: imperial *power* (Russia, Turkey, England, USA in der Loose-Fish-Liste, Kap. 89); *Gewalt* hält die juristisch-politische Schärfe (Staats-Gewalt, Walt-Anwendung), die *Stärke* fehlt — und korrespondiert mit *Macht* (s.o.) als doppelter Begriff für Souveränität und Zwang. |
| purple | purpurn | 2 | purpurn | D "the purple host", "the purple democrat" — Dickinson-Lieblingsfarbe; M "purple rascal" |
| single | einzig | 2 | einzig | D "The East put out a single flag"; M "loss of limb, or of a single life" |
| spirit | Seele | 2 | Geist | (Wechsel) — D "His spirit grew robust"; M Cock-Lane "spirit rappings" — *Geist* deckt geistig/spirituell breiter |
| today | heute | 2 | heute | M "Today all remain major figures"; standardisiert |

### 2c) 3-silbig (2)

| EN | DE-Vorschlag | Silben (DE) | DE-Vorschlag (Kontext) | Kontext-Beleg |
|---|---|---|---|---|
| another | ein andres | 3 | ein andres | D häufig — "another life"; M "another horn, pertaining to a land beast" |
| paradise | Paradies | 3 | Paradies | D "Paradise" wiederkehrend ("As Paradise"); M Mapple-Predigt |

### 2d) 4-silbig (1)

| EN | DE-Vorschlag | Silben (DE) | DE-Vorschlag (Kontext) | Kontext-Beleg |
|---|---|---|---|---|
| eternity | Unendlichkeit | 4 | Ewigkeit (3) | D "And taste eternity" + Kübler-Tradition — *Ewigkeit* näher an D-Theologie als *Unendlichkeit*; Silbenverlust hinzunehmen, oder *Ewigkeiten* (4, Plural) wenn Silbenstaffel zwingend |

### 2e) 5-silbig (1)

| EN | DE-Vorschlag | Silben (DE) | DE-Vorschlag (Kontext) | Kontext-Beleg |
|---|---|---|---|---|
| immortality | Unsterblichkeiten | 5 | Unsterblichkeit (4) | D "Immortality" als Schwellenbegriff (Kübler); Silbe-5 wäre nur durch Plural *Unsterblichkeiten* erreichbar — semantisch befremdlich, aber strukturell konsequent (so 1. Sp.) |

---

## 3. COURSE_START (3) — leitet `_compound_course` ein

> Original-Schema: *"fix upon the [SYL][SYL] course"*.
> Im Deutschen wird das Kompositum am Ende zum Wort verschmelzen
> (*"den Sackflossenkurs"*); deshalb muss `course` direkt am Kompositum
> hängen, was den Generator umbaut.

| EN | DE-Vorschlag | DE-Vorschlag (Kontext) | Generator-Form | Kontext-Beleg / Anmerkung |
|---|---|---|---|---|
| fix upon the | richte auf den | auf den [...] versessen | `('auf den ', ' versessen')` | M Kap. 36 "fixed purpose"; "fix upon" trägt das Obsessive Ahabs (*"my fixed purpose is laid with iron rails"*) — *versessen auf* fasst die Monomanie schärfer als das Wegweise-*richten* |
| cut to fit the | schneide zurecht den | auf den [...] zugerichtet | `('auf den ', ' zugerichtet')` | M Schiffsbau-Kontext; *zugerichtet* trifft das gewaltsam-zugepasste der Kompositum-Bildung |
| how to withstand the | wie zu trotzen dem | wie den [...] zu bestehen | `('wie den ', ' zu bestehen')` | M Pequod-Sturm; *bestehen* (Akk.) löst Kasus-Inkonsistenz und trifft existenzielles "withstand" |

**Strukturentscheidung nötig:** Entweder einheitlicher Kasus (alle Akk. oder
alle Dat.), oder Generator akzeptiert pro Phrase einen Artikel-Slot.

**Generator-Lösung:** `COURSE_START` enthält Tupel `(Präfix, Suffix)`.
Das Kompositum (Erstglied + Zweitglied + `Kurs`) rückt in den Slot
zwischen Präfix und Suffix ein. Bei Konsonantenkollision an einer
Komposita-Naht setzt der Generator einen Bindestrich und
kapitalisiert das folgende Glied (z. B. *Klecks-Skaldkurs*,
*Beutelbock-Kurs*). Doppelungen (b == c → z. B. *Beutelbeutelkurs*)
werden durch deterministische Verschiebung des zweiten Index um 1
vermieden.

---

## 4. SYLLABLE-Listen — Kompositionsmaterial für `_compound_course`

### 4a) DICKINSON_SYLLABLE (23)

| EN | DE-Vorschlag | Silben | DE-Vorschlag (Kontext) | Generator-Form | Kontext-Beleg |
|---|---|---|---|---|---|
| bard | Skald | 1 | Skald | — | D "the mysterious bard" — *Skald* hält Silbe und alteritärischen Klang; *Barde* nüchterner |
| bead | Perl | 1 | Perl | — | D Schmuck-/Tau-Topos; *Perl* (Apokope) |
| bee | Bien | 1 | Bien | Bienen *(Kasus-Stammform; Bienenstock-Tradition)* | D Bienen-Topos zentral ("the bumble-bee", "honey", "the goblin bee"); *Bien* (Goethe, dial.) |
| bin | Trog | 1 | Trog | — | (eigen) — Speicher-Topos |
| blot | Klecks | 1 | Klecks | — | D "How a small dusk crawls on the village / Till the houses blot" — *Klecks* trifft den fleckenartigen Verfall |
| blur | Schlier | 1 | Schlier | — | D "Would it blur the Christmas glee" — Verschleierung von Glanz; *Schlier* (Trübung) |
| buzz | Summ | 1 | Gesumm (2) | — | D "Buzz the dull flies on the chamber window" (Sterbezimmer) — onomatop. *Summ* trifft das Schwellen-Geräusch |
| curl | Lock | 1 | Kringel (2) | — | (eigen) — *Lock* würde mit Verb kollidieren; oder *Schweif* (1, m) — Silbenwechsel hinzunehmen |
| dirt | Dreck | 1 | Schmutz | — | (Wechsel) — D meist niedere/körperliche Sphäre; *Schmutz* trifft poetischen Ekel-Topos klarer als *Dreck* (umgangs.) |
| disk | Scheib | 1 | Scheib | Scheiben *(Kasus-Stammform; Scheibenwischer)* | D "Soundless as dots on a disk of snow" — *Scheib* (Apokope) erhält Bild der Schneescheibe |
| drum | Pauk | 1 | Trumm | — | (eigen) — D "A service like a drum / Kept beating, beating" — *Trumm* (südd.) trägt das Pochen besser als *Pauk* (zu militärisch) |
| fern | Farn | 1 | Farn | — | D "Fern-odors on untravelled roads" — Wald-Topos |
| film | Schleier | 2 | Häut (1) | Haut *(Singular; Hautcreme-Tradition)* | D "The thought beneath so slight a film / Is more distinctly seen" — *Häut* (Apokope) hält Silbe, trifft das Hauchige besser als *Schleier* |
| folk | Volk | 1 | Volk | — | D "common folk"; M Mannschafts-Kollektiv |
| germ | Keim | 1 | Keim | — | D "The germ of alibi" — Keim/Anlage |
| hive | Stock | 1 | Stock | — | (eigen) — Bienenstock-Sinn; alt: *Korb* — *Stock* kollidiert ggf. mit *plot/stem* |
| hood | Haub | 1 | Haub | Hauben *(Kasus-Stammform; Haubenadler)* | D Schutz-/Verbergens-Bild; *Haub* (Apokope) |
| husk | Hüls | 1 | Hüls | Hülsen *(Kasus-Stammform; Hülsenfrucht)* | D Hülle/Spreu-Topos; *Hüls* (Apokope) |
| jay | Häher | 2 | Häher | — | D Gedicht "THE BLUE JAY. No brigadier throughout the year / So civic as the jay" — *Häher* unverzichtbar; Silbenverlust hinzunehmen |
| pink | Rosa | 2 | Pink (1) | — | D Gedicht "MAY-FLOWER. Pink, small, and punctual" — Anglizismus *Pink* hier als Farbe etabliert (vgl. Kübler-Tradition); 1-silbig erhalten |
| plot | Plan | 1 | Plan | — | M "The plot of the narrative is scarcely worthy of the name" — *Plan* trifft Anschlag/Plot-Doppelheit |
| spun | Garn | 1 | Garn | — | D "It spun and spun, / And groped delirious, for morn" — *Garn* (Substantivierung) trägt Spinnen-Bild |
| web | Netz | 1 | Netz | — | M "a large and interesting web of narrative" — Erzählnetz |

### 4b) MELVILLE_SYLLABLE (31)

| EN | DE-Vorschlag | Silben | DE-Vorschlag (Kontext) | Generator-Form | Kontext-Beleg |
|---|---|---|---|---|---|
| bag | Sack | 1 | Sack | — | M Kap. 2 "The Carpet-Bag" — der Reisesack als Insignie der bürgerlichen Mobilität, mit der Ishmael die Walfangstadt Nantucket erreicht. Bürgerliche Verschiffung trifft Walfänger-Lohnarbeit. Die Kollision mit *sack* in derselben Liste (s. dort) ist im Englischen vorhanden und kann im Deutschen produktiv inszeniert werden — die Ungleichheit zwischen *Reise*-Sack und *Schiffs*-Sack als Klassenmarker. |
| buck | Bock | 1 | Stier | — | M "buck-horn handled Bowie-knives" — Hörnerinstrument-Konnotation, entkollidierung mit Ram |
| bunk | Pritsch | 1 | Pritsch | Pritschen *(Apokope→Kasus-Stammform)* | M Bradbury-Anekdote: "blinded and strapped to a bunk" — schmale Schlafstätte; *Pritsch* (Apokope) hält Silbe |
| cane | Rohr | 1 | Stab | — | M Ahab: "Give me something for a cane—there, that shivered lance will do" — Ahab improvisiert seinen Spazierstock aus der zerbrochenen Walfanglanze: das Werkzeug der Aneignung wird zum Herrschafts-Stab. *Stab* trägt im Deutschen Krückstock, Heerführer-Stab, Hirten-Stab, Bischofsstab — die ganze Kette der Befehls- und Disziplinar-Insignien. |
| chap | Kerl | 1 | Kerl | — | M "the harpooner is a dark complexioned chap" — *Kerl* trifft umgangssprachliche Walfänger-Diktion |
| chop | Hieb | 1 | Schlag | — | (Wechsel) — M "two hundred and fifty fins growing on each side of his upper chop" (Wal-Kiefer); aber idiomatisch *Hieb*; *Schlag* entkollidiert mit *dash* |
| dash | Strich | 1 | Strich | — | M "The wavy dash (~)" — typografischer *Strich* trägt zugleich Geste und Zeichen |
| dock | Dock | 1 | Dock | — | M "Greenland dock" — Hafen-Topos |
| edge | Schneid | 1 | Schneid | — | M "the top edge of a fore and aft sail"; Schiffstechnik — *Schneid* trifft Kante/Schärfe |
| fin | Floss | 1 | Floss | Flossen *(Apokope→Stammform; vermeidet Floß-Homophonie)* | M "gnomon-like fin": die Walflosse als Sonnenuhr-Zeiger, der Wal als kosmisches Maß-Wesen, das die Walfangindustrie zerteilt und verwertet. *Floss* (Apokope) hält Silbe; *Flosse* zerteilt sich in den Industrie-Begriff *Walflosse* (Handelsware, Walbein-Korsett, Speiseöl). |
| hag | Hex | 1 | Hex | Hexen *(Apokope→Kasus-Stammform; Hexenkessel)* | M "a sort of eating of his own gums like a chimney hag" — Hexen-Bild; *Hex* (Apokope) |
| hawk | Falk | 1 | Falk | Falken *(Apokope→Kasus-Stammform; Falkenauge)* | M "the black hawk darted away with his prize" — Raubvogel-Topos; *Falk* (Apokope) trifft besser als *Habicht* |
| hook | Hak | 1 | Hak | Haken *(Apokope→Vollform; Hakenkreuz-Tradition)* | M "gaff: A boat hook" — Greif-/Fang-Werkzeug; *Hak* (Apokope) |
| hoop | Reif | 1 | Reif | — | M "Hold up thy hoop, Pip, till I jump through it!" — Zirkus-/Spiel-Reif |
| horn | Horn | 1 | Horn | — | M Erzähleinschub Earl-of-Leicester (Walross-Horn) |
| howl | Heul | 1 | Geheul (2) | — | M "The long howl thrills me through!" — Wolfs-/Wolfsschar-Topos |
| iron | Eisen | 2 | Eisen | — | M Kap. 89: "two irons, both marked by the same private cypher" — die Harpune als markierender Eigentums-Erweis (das Stahl-Mal, das den freien Fisch zum festen macht). Verstärkt durch Kap. 37: "The path to my fixed purpose is laid with iron rails" — *Eisen* trägt die ganze Industrie-Topik (Harpune, Schiene, Maschine, Kapital-Werkzeug); Silbenverlust hinzunehmen. |
| jack | Knecht | 1 | Hein | — | M Kap. 45: *Jack* als austauschbarer Eigenname für Matrosen ("Jack" / "Tom" als beliebige Variante). Die Anonymisierung des Lohnarbeiters durch generische Anrede; im Deutschen *Bursch* (Apokope) trägt die abwertend-vertraulich-gönnerhafte Diktion der Schiffsherren. Alt: Knecht (Eigentums-Topos noch deutlicher, aber feudal statt kapitalistisch konnotiert). |
| jaw | Maul | 1 | Maul | — | M Walkiefer-Topos zentral (jaw of leviathan); Rathjen-Tradition |
| kick | Tritt | 1 | Tritt | — | M "my first kick" (Pequod-Anekdote); *Tritt* hält Silbe und Schlag-Bild |
| lime | Kalk | 1 | Kalk | — | M Abrieb-/Verkalkungs-Topos |
| loon | Tölpel | 2 | Narr | Narren *(Kasus-Stammform; Narrenschiff)* | M Kap. 129: "Peace, thou crazy loon" (Manxman zu Pip) — Pip, der schwarze Schiffsjunge, fällt nach seiner Aussetzung im Meer in einen Wahn, der bei Melville *einsichtiger* erscheint als die Vernunft der weißen Offiziere. *Narr* trägt diese sozial-traumatische Dimension (vgl. Shakespeares Narren als Wahrheitsstellen); der Wahnsinn der Untergebenen als Symptom der Gewalt, die sie erleidet. |
| lurk | Schleich | 1 | Schleich | — | M "in Ahab, there seemed not to lurk the smallest social arrogance" — *Schleich* (Apokope) trägt das Verborgene |
| milk | Milch | 1 | Milch | — | M "feminam mammis lactantem" Anspielung; Mutter-/Brust-Topos |
| pike | Spieß | 1 | Spieß | — | M "stiff as a pike-staff" — Stab-/Waffen-Konnotation. *Spieß* trägt im Deutschen die Doppel-Konnotation der proletarischen Bewaffnung (Sansculotten-Pike, Bauernkriegs-Spieß) und der Spieß-/Stoßwaffe der Walfänger; politisch dichter als das nur ichthyologische *Hecht*. |
| rag | Lump | 1 | Lump | Lumpen *(Kasus-Stammform; Lumpenproletariat)* | M Kap. 1: "a purse is but a rag unless you have something in it" — die ironische Inversion bürgerlicher Geld-Werte (Geldbeutel ohne Inhalt = Lumpen). *Lump* trägt im Deutschen den ganzen Lumpen-Komplex: Lumpenproletariat, Lumpenhändler, Lumpenpapier (Schreibmaterial aus Stofflumpen) — die Material-Geschichte der unterworfenen Arbeit. |
| rail | Reling | 2 | Reling | — | M nautisch ("a removable bar fitted in a hole in the rail of a ship"). Im englischen Original schwingt zugleich die Eisenbahn-*rail* mit, die in Kap. 37 zentral wird ("The path to my fixed purpose is laid with iron rails") — die Verzahnung von Walfang-Schiff und Industrie-Schiene als zwei Apparate kapitalistischer Festlegung. Im Deutschen läßt sich diese Doppelheit nicht in einem Wort halten; *Reling* nautisch klar, der Eisenbahn-Echo geht über das benachbarte *iron* (s.o.). |
| ram | Widder | 2 | Bock | — | (Wechsel + neuer Vorschlag) — M "ram a skewer through their necks" als Verb (rammen) hier substantiviert; *Bock* (m) verschiebt Kollision auf 4b *buck*, das mit *Stier* (1) entkollidiert werden kann; **Strukturentscheidung nötig** |
| sack | Sack | 1 | Beutel (2) | — | (Wechsel zur Entkollidierung) — M "Queequeg's canvas sack"; *Beutel* hält semantisch näher am Stoff-Behältnis und entkollidiert mit *bag* (=*Sack*) |
| salt | Salz | 1 | Salz | — | M "the salt spray dashing on our brows" — See-Salz-Topos |
| tool | Werk | 1 | Zeug | — | M "A grapnel is a tool consisting of several hooks for grasping and holding" — das Greif- und Festhalte-Werkzeug der Walfangindustrie. *Zeug* trägt im Deutschen den ganzen Bedeutungsraum der Produktionsmittel: Werkzeug, Schiffszeug, Kriegszeug, Lumpenzeug. Politisch dichter als das individuell-handwerkliche *Werk*. |

---

## 5. DICKINSON_LESS_LESS — die `-less`/`-los`-Hürde

> **Strukturproblem:** `-los` produziert idiomatische Adjektive nur bei
> Nomen (Schuld → schuldlos), nicht bei Verben oder Verbalsubstantiven
> (efface, perturb, repeal). Außerdem haben einige `-los`-Bildungen im
> Deutschen feste idiomatische Bedeutungen, die mit Dickinson kollidieren
> (*grundlos* = "ohne Grund/Anlass", nicht "ohne Sockel"; *fruchtlos* =
> "vergeblich", nicht "ohne Frucht"; *pausenlos* = "unaufhörlich"). Hier Suffix-Wechsel auf *-fern* (Celan-Echo:
>*kunstfern, todfern*).

### 5a) 1-silbig (44)

| EN | DE-Vorschlag | `-los`-Bildung | DE-Vorschlag (Kontext) | Generator-Form | Kontext-Beleg |
|---|---|---|---|---|---|
| art | Kunst | kunstlos | kunstlos | — | D "Have I the art to say"; M "art of shipbuilding" — *kunstlos* idiomatisch |
| base | Grund | grundlos | standlos | — | M "base of the Eddystone" (Leuchtturmsockel) — *grundlos* hält Doppelsinn (ohne Sockel/ohne Anlass) |
| blame | Schuld | schuldlos | schuldfrei | — | M "blame not Stubb too hardly"; D "Without a stint, without a blame" — *schuldlos* trifft Beschuldigungs-Sinn (mit Kollisionshinweis zu *guilt*) |
| crumb | Krume | krumenlos | brotlos | — | (Wechsel zur Idiomatik) — D "Give the one in red cravat / A memorial crumb"; *brotlos* idiomatisch tragender |
| cure | Heil | heillos | heillos | — | M "sovereign cure for all colds" (Stubbs Gin-Mischung) — *heillos* idiomatisch ("desolat") |
| date | Frist | fristlos | fristfern | — | (eigen) — D "The date, and manner of the shame" (jurist.) — *datumslos* präziser bei zeitlich Festgesetztem |
| death | Tod | todlos | todesfern | — | M "death-grasp"; D "Life is but life, and death but death" — *todlos* (poet.) |
| drought | Dürre | dürrelos | dürrefern | — | D "the drought is destitute, / But then I had the dew" — *dürrelos* eigenwillig, aber tragbar |
| fail | Fehl | fehllos | fehlfrei | — | D "If I should fail, what poverty!" — *fehllos* trifft Versagensfreiheit besser als *fehlerlos* |
| flesh | Fleisch | fleischlos | fleischfern | — | D "The flesh surrendered, cancelled, / The bodiless begun" — *fleischlos* klingt am Übergang zur Körperlosigkeit |
| floor | Boden | bodenlos | bodenlos | — | D "And narrow at the floor"; M Schiffsbau-*kelson* — *bodenlos* idiomatisch ("abgründig") trifft Dickinsons Tiefen-Topos |
| foot | Fuß | fußlos | fußlos | — | D "The accent of a coming foot, / The opening of a door"; *fußlos* leicht abweichend, aber idiomatisch |
| frame | Rahmen | rahmenlos | rahmenlos | — | D "his frame was dust"; M "shock running through all my frame" — *rahmenlos* hält Idiomatik |
| fruit | Frucht | fruchtlos | fruchtlos | — | D "FORBIDDEN FRUIT. Forbidden fruit a flavor has" — *fruchtlos* klingt verbotsnah ("vergeblich") |
| goal | Ziel | ziellos | ziellos | — | D "THE GOAL. Each life converges to some centre"; M "horizontal goal" — *ziellos* idiomatisch |
| grasp | Griff | grifflos | unfasslich (3) | — | D "extraordinary grasp and insight"; M "death-grasp" — *unfasslich* trifft die Erfahrung des Nicht-Greifens, *grifflos* zu konkret-mechanisch (Silbenverlust hinzunehmen) |
| guile | List | listlos | arglos | — | (Wechsel) — D "guile is where it goes" — *arglos* idiomatisch und bewahrt die List-/Tücke-Negation |
| guilt | Reue | reuelos | reuelos (3) | — | (Wechsel zur Entkollidierung) — M "guilt and guiltlessness"; D "Mine, by the grave's repeal" — *reuelos* trage zweites *schuldlos* |
| hue | Farb | farblos | farblos | — | M "a corpse's hue"; D "Nature rarer uses yellow / Than another hue" — *farblos* idiomatisch |
| key | Schlüssel | schlüssellos | schlüssellos | — | D "the sexton keeps the key to" (Tod als Sakristan); *schlüssellos* trifft den Verschluss |
| league | Bund | bundlos | bundlos | — | D "the divine intoxication / Of the first league out from land" (Seemeile, *Liga*); *bundlos* poet. — alt: *meilenlos* |
| list | Liste | listenlos | listenlos | — | D "But God on his repealless list / Can summon every face" — *listenlos* trifft den Rechen-/Buchführungs-Sinn |
| need | Not | notlos | notfrei | — | D "Requires sorest need" — *notlos* poet. (gegen idiomatisches *bedürfnislos*) |
| note | Ton | tonlos | tonlos | — | M "key-note to an orchestra"; D "tied in little fascicules" (Notizen) — *tonlos* idiomatisch |
| pang | Pein | peinlos | schmerzlos | — | (Wechsel) — D "For pang of jealousy" (Heftigkeit); M "great hearts sometimes condense to one deep pang" — *schmerzlos* idiomatisch (peinlos = ungebräuchlich) |
| pause | Pause | pausenlos | pausenlos | — | M "A brief pause ensued"; D "The maimed may pause and breathe" — *pausenlos* idiomatisch ("unaufhörlich") |
| phrase | Phrase | phrasenlos | wortlos | — | (Wechsel) — D Project-Gutenberg-Erwähnung; M "the phrase 'oh, no!'" — *wortlos* trifft den Mangel an Ausdruck besser |
| pier | Steg | steglos | steglos | — | M "leaning against the spiles; some seated upon the pier-heads" (Hafen) — *steglos* poet. |
| plash | Platsch | platschlos | klanglos | klanglos *(Doppelung mit sound — Kontext-Spalte beibehalten)* | (Wechsel) — *plash* in unseren Texten kaum belegt; *klanglos* (vgl. *sound*) trifft das wassergeräuschlich-leise — Kollision mit *sound* annehmen oder *spritzlos* (eigen) |
| price | Preis | preislos | preislos | — | M Kap. 2: "be sure to inquire the price, and don't be too particular" (Ishmaels Quartiersuche) — *preislos* trägt im Deutschen die produktive Doppelheit "ohne Preis" / "unbezahlbar": das, was sich der Bewertung entzieht, kann beides sein — wertloses Material oder das, was den Markt sprengt. Politisch zentrale Ambivalenz. |
| shame | Scham | schamlos | schamlos | — | M "shame upon all cowards"; D "There is a shame of nobleness" — *schamlos* idiomatisch |
| shape | Form | formlos | gestaltlos (3) | — | (Wechsel) — D "I think just how my shape will rise"; M "to shape these Phantasms so vividly" — *gestaltlos* trifft Dickinsons Auferstehungs-Bild präziser als *formlos*; Silbenverlust |
| sight | Blick | blicklos | blicklos | — | D "you saturated sight"; M "in full sight of it" — *blicklos* idiomatisch (Celan-Echo) |
| sound | Klang | klanglos | klanglos | klanglos *(Doppelung mit plash — Kontext-Spalte beibehalten)* | D "a caravan of sound" (Sphärenmusik); M "to sound is to dive to the bottom" — *klanglos* idiomatisch |
| star | Stern | sternlos | sternlos | — | D "Here a star, and there a star, / Some lose their way" — *sternlos* idiomatisch (Schiffer-Topos: ohne Orientierung) |
| stem | Stamm | stammlos | wurzellos (3) | — | (Wechsel) — D "And strut upon my stem"; M "from stem to stern" — *wurzellos* trägt Existenz-Topos besser; Silbenverlust |
| stint | Maß | maßlos | maßlos | — | D "Without a stint, without a blame" — *maßlos* idiomatisch und doppeldeutig (Maß / Begrenzung) |
| stir | Regung | regungslos | regungslos | — | D "New fingers stir the sod"; M "stir nothing, but lash everything" — *regungslos* idiomatisch |
| stop | Halt | haltlos | haltlos | — | D "If I can stop one heart from breaking"; M "Avast" — *haltlos* idiomatisch (mehrfach: ohne Halt / unaufhörlich) |
| swerve | Schwung | schwunglos | unaufhaltsam (4) | — | M Ahab "ye cannot swerve me, else ye swerve yourselves" + Kap. 37 "fixed purpose is laid with iron rails" — *unaufhaltsam* trifft die kapitalistische Antriebs-Topik (das Subjekt, das nicht aufgehalten werden kann), korrespondiert mit *swerve me?* (s. Liste 1) und mit *iron* (s. 4b). Silbenüberschuss hingenommen. |
| tale | Mär | märlos | märchenlos (3) | — | M "twice told tale"; D "the tale of dews" — *märlos* poet. (Apokope) |
| taste | Geschmack | geschmacklos | geschmacklos (3) | — | M "manifestations of bad taste"; D "I taste a liquor never brewed" — *geschmacklos* idiomatisch (geschmacklich/ästhetisch) |
| thread | Faden | fadenlos | fadenlos | — | D "the bewildering thread!" (Webteppich); M "darker thread with the story" — *fadenlos* idiomatisch (Erzähl-/Web-Topos) |
| worth | Wert | wertlos | wertlos | — | M "what the author does not know about the sea, is not worth knowing" — *wertlos* idiomatisch |

### 5b) 2-silbig (27)

| EN | DE-Vorschlag | `-los`-Bildung | DE-Vorschlag (Kontext) | Generator-Form | Kontext-Beleg |
|---|---|---|---|---|---|
| arrest | Halt | (s. 5a) | bannfrei | — | (eigen) — *arrest* bei D mit Festhalten/Bannen-Konnotation; "bannfrei" trägt den Halte-Aspekt |
| blanket | Decke | deckenlos | deckenlos | — | M "before we ride to anchor in Blanket Bay" (= zu Bett gehen); D "Batschia in the blanket red" — *deckenlos* trägt Schlaf-/Bett-Privation |
| concern | Sorge | sorgenlos / sorglos | sorglos | — | D "The pedigree of honey / Does not concern the bee"; M "Much concern was shown" — *sorglos* idiomatisch und kürzer |
| costume | Kostüm | kostümlos | kostümlos | — | D "Their costume, of a Sunday"; M Queequeg "in the Highland costume" — *kostümlos* hält Bild der Verkleidung |
| cypher | Chiffre | chiffrelos | chiffrelos | — | M Kap. 89 "two irons, both marked by the same private cypher" — *chiffrelos* trägt geheimzeichen-frei; alt: *zeichenlos* |
| degree | Grad | gradlos | gradlos | — | M "almost all men in their degree"; D "What opulence the more / Had I, a humble maiden, / Whose farthest of degree" — *gradlos* hält die Stufungs-Negation |
| desire | Begehr | begehrlos | begehrlos | — | D "the desire of her personal friends"; M "no desire to enlarge the circle" — *begehrlos* poet. tragend |
| dower | Mitgift | mitgiftlos | mitgiftlos | — | D "Say quick, that I may dower thee" (Versuch, sich der Geliebten zu vermachen); *mitgiftlos* hält Brautgabe-Topos |
| efface | Tilgung | tilgungslos | löschfern | — | (Wechsel zur Privations-Umkehr) — *efface* deverbal: nicht direkt mit *-los*; *unauslöschbar* trifft die emphatische Nicht-Tilgbarkeit; |
| enchant | Zauber | zauberlos | zauberlos | — | D häufiger Bezauberungs-Topos; *zauberlos* idiomatisch tragbar |
| escape | Flucht | fluchtlos | fluchtlos | — | D Gedicht "X. ESCAPE. I never hear the word 'escape' / Without a quicker blood"; M "To escape the pressure of creditors" — *fluchtlos* trifft die ausweglose Lage |
| fashion | Mode | modelos | modelos | — | D "And newer fashions blow"; M "a singularly common fashion" — *modelos* knapp idiomatisch |
| flavor | Würze | würzelos | würzlos | — | M "Forbidden fruit a flavor has"; "fishy flavor to the milk" — *würzlos* (1-Silben-Verlust hingenommen) idiomatischer als *würzelos* |
| honor | Ehre | ehrenlos | ehrlos | — | (Verkürzung) — M "Bashaw: Or pasha, a Turkish title of honor" — *ehrlos* idiomatischer und schärfer als *ehrenlos* |
| kinsman | Sippe | sippenlos | sippenlos | — | D "Near kinsman to herself" (Heide/Pflanze als Verwandte) — *sippenlos* trägt Verwandtschafts-Privation |
| marrow | Mark | marklos | marklos | — | M "marrow in his bones to quiver"; D "The bone that has no marrow" — *marklos* idiomatisch tragbar (vgl. *kraftlos*, *marklos* = fad) |
| perceive | Wahrnehm | – | unmerklich (3) | — | (Privations-Umkehr) — D "enlightened to perceive / New periods of pain"; M "quick to perceive a horror" — *unmerklich* fasst Nicht-Wahrnehmbarkeit; Silbenüberschuss |
| perturb | Störung | störungslos | unstörbar (3) | — | (Privations-Umkehr) — *unstörbar* trifft den emphatischen Unverwirrbar-Sinn besser als *störungslos* |
| plummet | Senkblei | senkbleilos | grundlos (2) | — | (Wechsel) — M "beyond the reach of any plummet" (Walfisch in Tiefe) — *grundlos* (= unausgelotet) trifft die Tiefen-Unausmessbarkeit; Kollision mit *base/grundlos* (5a) — Generator muss entscheiden |
| postpone | Aufschub | aufschublos | unaufschiebbar (5) | — | (Privations-Umkehr) — M "could he so tranquillize his unquiet heart as to postpone all intervening quest" — *unaufschiebbar* trifft Ahabs Drang |
| recall | Ruf | ruflos | unrufbar (3) | — | (Privations-Umkehr) — M "many of which impressions I cannot now recall"; *unrufbar* trifft Nicht-Erinnerbarkeit; alt: *erinnerungslos* (5) |
| record | Aufzeichn | – | spurlos (2) | — | (Wechsel) — D "Lingers to record thee"; M "thing placed upon authoritative record" — *spurlos* trifft Aufzeichnungs-Privation |
| reduce | Minderung | – | unverminderbar (5) | — | (Privations-Umkehr) — M "any of the things that literary criticism would reduce it to" — *unverminderbar* trifft Reduktions-Negation |
| repeal | Widerruf | widerruflos | unwiderruflich (5) | — | D: "Mine, here in vision and in veto! / Mine, by the grave's repeal" — Dickinsons *Mine*-Gedicht als Liste der Aneignungs-Modi (Vision, Veto, Grab-Widerruf). Politisch ist *Repeal* genau die Geste, die das gesetzte Eigentum *zurücknimmt* — die Bewegung der Enteignung der Enteignung. *Unwiderruflich* hält paradox die Endgültigkeit dieser Rücknahme. |
| report | Bericht | berichtlos | berichtlos | — | M "the spies Moses sent... bring back the report"; D "Without external sound" / "report of land" — *berichtlos* tragbar; alt: *kundlos* |
| retrieve | Bergung | bergungslos | unbergbar (3) | ungeborgen *(Kollisionsauflösung mit retriever — vorher unbergbar)* | (Privations-Umkehr) — D "Retrieve thine industry"; *unbergbar* trifft Nicht-Wiederholbarkeit; Silbenüberschuss |
| tenant | Mieter | mieterlos | mieterlos | — | D: "THE RAT. The rat is the concisest tenant. / He pays no rent, — / Repudiates the obligation, / On schemes intent" — die Ratte als parasitärer Mieter, der den Vertrag verweigert. Das knappste denkbare Modell einer Aneignung gegen das Eigentumsrecht: *concisest tenant* heißt zugleich kürzester und konzentriertester. *Mieterlos* hält dieses Vertrags-Verweigerungs-Motiv. |

> **Bilanz 5b:** Mindestens 8 deverbale Bildungen (efface, perceive,
> perturb, postpone, record, reduce, repeal, retrieve) lassen sich nicht
> sinnvoll mit *-los* verbinden. Hier ist eine **Strukturentscheidung**
> fällig: entweder Liste 5b drastisch kürzen (= weniger Permutationen,
> verändert das Werk) oder Generator-Funktionen auf eine andere
> Privations­struktur umstellen.

### 5c) 3-silbig (2)

| EN | DE-Vorschlag | `-los`-Bildung | DE-Vorschlag (Kontext) | Generator-Form | Kontext-Beleg |
|---|---|---|---|---|---|
| latitude | Breitengrad | – | breitenlos (3) | — | M häufig nautisch-geographisch ("latitudes of buck-horn");  trifft die geographisch-metaphorische Weite |
| retriever | Apportier | – | unbergbar (3) | unwiederbringlich *(Kollisionsauflösung mit retrieve — alt aus Doc übernommen)* | (Wechsel zu 5b *retrieve*) — Hunde-Konnotation streichen, Privations-Bildung; alt: *unwiederbringlich* (5) |

---

## 6. UP_VERB (12) — Verbpaare in `_rise_and_go`

> Schema: *"X-less Y and Z"* → *"Xlos Y und Z"*. Im Deutschen
> Infinitive (oder bare Stems wie Englisch), gepaart durch *und*.

| EN | DE-Vorschlag | DE-Vorschlag (Kontext) | Kontext-Beleg |
|---|---|---|---|
| bask | sonnen | sonnen | D "To bask the centuries away / Nor once look up for noon"; M "as a traveller in winter would bask before an inn fire" — Reflexiv-Problem bleibt; Generator kann *sich* mitführen oder *bask*-Vorschlag *träumen* (eigen) prüfen |
| chime | klingen | läuten | (Wechsel) — D "The everlasting clocks / Chime noon" — *läuten* trifft das Glockenmotiv präziser als das allgemeine *klingen* |
| dance | tanzen | tanzen | D "He danced along the dingy days"; M "St. Vitus' dance" |
| go | gehen | gehen | D "And then, to go to sleep"; M "Pip does go mad" |
| leave | scheiden | scheiden | D "And leave the soul alone"; M "to leave one's own world and enter another" — *scheiden* trifft das existenzielle Verlassen besser als *lassen* |
| move | regen | regen | M "To move a horror skillfully" — *regen* trifft die innere Bewegung |
| rise | steigen | steigen | D "There are, that resting, rise"; M "the diver rises... no more to rise for ever" — *steigen* hält Vertikale |
| sing | singen | singen | D "To hear an oriole sing"; M "let the Typhoon sing" |
| speak | sprechen | sprechen | D "Too jostled were our souls to speak"; M "Four messengers speak to Job" |
| step | schreiten | schreiten | D "prodigious, step / Around a pile of mountains"; M "any one step forth" — *schreiten* trifft die feierliche Geste |
| turn | wenden | wenden | D "When landlords turn the drunken bee"; M "turn and tack" — *wenden* nautisch und idiomatisch |
| walk | wandeln | wandeln | D "his golden walk is done" (Sonne); M "they walk out of the fire unscathed" — *wandeln* (Kübler-Tonfall) hält biblisch-poetischen Ton |

---

## 7. BUT_BEGINNING (3) + BUT_ENDING (4) — `_but`

Schema: *"but X-less is the Y"* → *"doch Xlos ist die/der/das Y"*.

### 7a) BUT_BEGINNING

| EN | DE-Vorschlag | DE-Vorschlag (Kontext) | Kontext-Beleg |
|---|---|---|---|
| but | doch | doch | D häufig — "But why compare? I'm wife! stop there!" — *doch* trifft den Dickinson-Wendepunkt knapper als *aber* |
| for | denn | denn | D "For pang of jealousy"; *denn* hält kausal-poetischen Ton |
| then | dann | dann | D "And then, those little anodynes"; *dann* hält temporale Folge |

### 7b) BUT_ENDING

| EN | DE-Vorschlag | Genus | DE-Vorschlag (Kontext) | Generator-Form | Kontext-Beleg |
|---|---|---|---|---|---|
| earth | Erde | f | Erde | `('die', 'Erde')` *(Genus-Artikel für `_but`)* | D "earth seems so / To those in heaven now"; M "carking cares of earth" |
| sea | See | f | See | `('die', 'See')` | M Job-Motto, Pequod-Untergang; D "BY THE SEA. I started early, took my dog" — Rathjen-Tradition (See gegen Meer) |
| sky | Himmel | m | Himmel | `('der', 'Himmel')` | D "the brain is wider than the sky"; M "the air, the sky, the sea" — vollständig (gegen 2a *Blau*: in 7b ist *Himmel* tragender, weil Artikel *der* mitläuft) |
| sun | Sonne | f | Sonne | `('die', 'Sonne')` | M "shadow of the degrees... in the sun dial of Ahaz"; D "Leaning against the sun!" |

> **Genus-Problem:** Original *"is the X"* → im Deutschen *"ist die Erde / die See / der Himmel / die Sonne"*. Generator muss pro Token den Artikel mitführen.

---

## 8. NAILED_ENDING (11) — `_nailed`

Schema: *"nailed to the X"* → *"genagelt an die/den/das X"*. Bezugsstelle: Doublonen-Szene Moby-Dick Kap. 36 (*"This was the Spanish ounce of gold worth sixteen dollars … nailed to the mast"*) — die Wertfetisch-Szene par excellence: Ahab nagelt das Goldstück als Belohnung für das erste Sichten Moby Dicks an den Hauptmast, jeder Mannschafts-Mensch tritt heran und liest in der Münze sein eigenes Begehren. Die *NAILED*-Liste sammelt die Orte, an denen Wert, Macht und Bestrafung *fixiert* werden.

| EN | DE-Vorschlag | Genus | DE-Vorschlag (Kontext) | Generator-Form | Kontext-Beleg |
|---|---|---|---|---|---|
| coffin | Sarg | m | Sarg | `('den', 'Sarg')` *(Akk-Artikel für `_nailed`)* | M Schluß: "the coffin life-buoy shot lengthwise from the sea, fell over, and floated by my side" — Queequegs Sarg, ursprünglich für seinen Tod gezimmert, wird zur Rettungsboje und trägt Ishmael durch die Tage nach dem Untergang. Das Werkzeug der Bestattung als Reproduktionsbedingung des Überlebenden — die Pequod-Wirtschaft frißt ihre Mannschaft auf, der eine Erzähler überlebt am Material des Toten. |
| deck | Deck | n | Deck | `('das', 'Deck')` | M Kap. 36: das Deck als Bühne der Doublonen-Szene; das Deck ist der Arbeitsplatz, an dem die Befehle Ahabs in Mannschafts-Bewegung übersetzt werden — der Raum kapitalistischer Produktion, in dem Wert genagelt wird. |
| desk | Pult | n | Pult | `('das', 'Pult')` | M: "the Captain at his busy desk, hurriedly making out his papers for the Customs" — der Schreibtisch als Verwaltungsapparat, an dem die Walfangbeute in Zoll-Papiere übersetzt wird. *Pult* trägt zugleich Schul-/Kanzel-/Steuermanns-Pult: die Insignien der schreibenden Macht. |
| groove | Furche | f | Furche | `('die', 'Furche')` | M: "the line ran through the groove;—ran foul" — die Walfangleine, die durch die Bug-Nut läuft und die Männer ins Wasser reißen kann; der Verwertungs-Strom als physische Bahn. D: "The brain within its groove / Runs evenly and true; / But let a splinter swerve, / 'T were easier for you / To put the water back" — die Furche als Bahn der Vernunft, die ein Splitter aus der Spur bringt. *Furche* hält beide Pflug-/Bahn-/Hirn-Bedeutungen. |
| mast | Mast | m | Mast | `('den', 'Mast')` | M Kap. 36: an den Mast wird die Doublone genagelt — der Mast als zentrale Achse, an die der Wertfetisch befestigt wird, damit alle Blicke der Mannschaft auf ihn ausgerichtet werden. Ein floating panopticon des Geldes. |
| spar | Spiere | f | Spiere | `('die', 'Spiere')` | M nautisch (boom, gaff, yard); D: "Two swimmers wrestled on the spar / Until the morning sun, / When one turned smiling to the land. / O God, the other one!" — die Spiere als Trümmerstück, an das sich der Schiffbrüchige klammert: das, was vom Schiffswrack der kapitalistischen Akkumulation übrig bleibt und überleben hilft. Der Werktitel *Sea and Spar Between* nimmt genau diesen Punkt — die Position *zwischen* dem Meer und dem Holz, das einen trägt. (Rathjen *Spiere*, Jendis *Rah*.) |
| pole | Pfahl | m | Pfahl | `('den', 'Pfahl')` | M: "harpoon-pole sticking in him" — der Pfahl als ins Walfleisch gerammter Eigentums-Erweis (vgl. *fast-fish*: *fast to it*). *Pfahl* trägt Stamm-/Mahn-/Marter-Pfahl: die ganze Kette der Pfählungs-Strafen, an die der Gegenstand fixiert wird. |
| plank | Planke | f | Planke | `('die', 'Planke')` | M: "the planing in the world could make eider down of a pine plank" — Planke als Material, das hobelnd zugerichtet wird (Schiffsbau als Holz-Verarbeitung). D: "I stepped from plank to plank / So slow and cautiously" — die einzelne Planke als unsichere Stand-Möglichkeit. Beidseitig zentral. |
| rail | Reling | f | Reling | `('die', 'Reling')` | M nautisch ("fasten it at the rail"): die Reling als Grenze zwischen Schiff und Meer, an der die Pin gezurrt wird, an der das Tau läuft. Politisch: die Schwelle, an der die Mannschaft an die Beute (oder die Beute an die Mannschaft) gebunden wird. |
| room | Kammer | f | Kammer | `('die', 'Kammer')` | M: "the public room" (Wirtshaus-Schank), "the further angle of the room" (Kapitäns-Kabine); D: "Elysium is as far as to / The very nearest room, / If in that room a friend await / Felicity or doom" — *Kammer* hält die Klassen-Topografie des Schiffs (Kapitäns-Kammer / Mannschafts-Logis) und die schwellen-haftige Innenraum-Topik bei Dickinson. |
| sash | Schärpe | f | Schärpe | `('die', 'Schärpe')` | M: "trailing behind like his sash" (Offiziers-Schärpe) — die textile Insignie der Befehlsgewalt; Schärpe als getragene Hierarchie-Markierung, an die genagelt zu sein heißt: in den Befehls-Apparat eingenäht zu sein. |

---

## 9. Entscheidungen (Zusammenfassung)

Generell gilt die Spalte DE-Vorschlag (Kontext) als zu verwendende Übersetzung.

1. **Generator-Funktionen anpassen:**

   - `_one_noun` — Artikel-Behandlung (weglassen vs. mitführen)

   - `_compound_course` — Artikel-Slot pro `COURSE_START`-Phrase

   - `_but` — Genus-bewusster Artikel vor `BUT_ENDING`

   - `_nailed` — wie `_but`

   - `_rise_and_go` — `-los`-Bildung oder Strukturwechsel

     → Kasusproblem wurde aufgelöst. Wo nötig, Artikel für Genus im Generator berücksichtigen.

2. **`-less`-Privation grundsätzlich klären:**
   - Variante A: nur idiomatische `-los`-Bildungen zulassen (Liste 5b
     auf ~8 Tokens schrumpfen) → kleineres kombinatorisches Raum
     
   - Variante B: Suffix-Wechsel zu *-fern* / *-leer* (poetisch, aber
     verschiebt das Werk Richtung Celan)
     
   - Variante C: Konstruktionswechsel zu *"ohne X"* — bricht Versmaß

     → pragmatische Einzelfallentscheidung in der Spalte berücksichtigen.

3. **Kanonische Übersetzungen verifizieren:**
   - Rathjen *Moby-Dick*: Kap. 36 (*nailed to the mast*), Kap. 37
     (*swerve me*), Kap. 89 (*fast-fish/loose-fish*)
   - Kübler *Dickinson sämtliche Gedichte*: Bestätigung der
     Tonfall-Wahl bei *Pein, Wonne, Früh, Glaub, Ros*
   - Celan *Übersetzungen* (Auswahl Dickinson): falls *du -- auch --*
     dort vorkommt

     → gelöst, Spalte DE (Kontext) enthält Ergebnis

4. **Kollisionen auflösen:** `bag/sack`, `buck/ram`, `chop/dash`,
   `Schuld` (5a `blame` / 5b `guilt`), `Sinn` (2a `mind` / `thought`).

   → aufgelöst

5. **Silbenverluste quantifizieren:** in 2d/2e und an Einzelstellen
   in Liste 4 — entscheiden, ob die metrische Staffelung
   (1→2→3→4→5) im Deutschen aufgeweicht oder neu kalibriert wird.

   → es gibt keine 5-silbigen Worte mehr, Generator muss hier umgebaut werden.

---

*Datei: `generation/Stanza_DE_Uebersetzung.md` — Stand 2026-04-30 (Kontext-Spalte ergänzt)*
