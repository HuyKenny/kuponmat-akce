"""Categories, product types and brands — rule based (keywords), like Kupi's /slevy/<kategorie> + /sleva/<produkt>.

* CATEGORIES: top level (slug, name). Every product type belongs to one.
* TYPES: (slug, name, name in "v akci" sentence, category, include regexes, exclude regexes). The first matching type
  wins, so specific types go before general ones ("čokoládové bonbony" before "čokoláda"). Regexes run on the
  normalized title (lowercase, no diacritics). Slugs of the 32 original /akce/<slug>/ pages are kept.
* BRANDS: known brand names; a product page "<type> <brand>" (cokolada-milka) is created when both are known.
"""
from __future__ import annotations

import re
import unicodedata


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")


CATEGORIES = [
    ("ovoce-a-zelenina", "Ovoce a zelenina"),
    ("maso-a-ryby", "Maso, drůbež a ryby"),
    ("uzeniny-a-lahudky", "Uzeniny a lahůdky"),
    ("mlecne-vyrobky-a-vejce", "Mléčné výrobky a vejce"),
    ("pecivo", "Pečivo"),
    ("trvanlive-potraviny", "Trvanlivé potraviny"),
    ("sladkosti-a-snacky", "Sladkosti a slané snacky"),
    ("mrazene-potraviny", "Mražené potraviny"),
    ("kava-a-caj", "Káva a čaj"),
    ("nealko-napoje", "Nealko nápoje"),
    ("pivo-a-vino", "Pivo a víno"),
    ("alkohol", "Alkohol"),
    ("drogerie", "Drogerie a úklid"),
    ("kosmetika", "Kosmetika a hygiena"),
    ("pro-deti", "Pro děti"),
    ("mazlicci", "Mazlíčci"),
    ("domacnost", "Domácnost a kuchyně"),
    ("elektro", "Elektro"),
    ("obleceni", "Oblečení a obuv"),
    ("hracky", "Hračky"),
    ("dum-a-zahrada", "Dům, dílna a zahrada"),
    ("sport", "Sport a volný čas"),
]
CAT_NAME = dict(CATEGORIES)

# slug, name, phrase (genitive-ish for sentences), category, include, exclude
T = [
    # --- sladkosti (before dairy/fruit: "banány v čokoládě", "jogurtová tyčinka")
    ("adventni-kalendare", "Adventní kalendáře", "adventní kalendáře", "sladkosti-a-snacky", [r"adventni kalendar"], []),
    ("bonboniery", "Bonboniéry", "bonboniéry", "sladkosti-a-snacky", [r"bonbonier", r"pralink", r"ferrero rocher", r"merci\b", r"raffaello", r"mon cheri"], []),
    ("cokoladove-tycinky", "Čokoládové tyčinky", "čokoládové tyčinky", "sladkosti-a-snacky", [r"tycink", r"\bmars\b", r"snickers", r"twix", r"bounty", r"kit ?kat", r"\bdeli\b", r"margot", r"kofila", r"fidorka", r"knoppers"], [r"mysli", r"musli", r"cereal", r"proteinov", r"sypk", r"vonn", r"\bglade"]),
    ("cokolada", "Čokoláda", "čokoládu", "sladkosti-a-snacky", [r"cokolad", r"\bmilka\b", r"\blindt\b", r"orion", r"ritter sport", r"\btoblerone", r"\bkinder\b", r"m&m", r"winter minis", r"\bfigaro", r"studentska"], [r"napoj", r"mleko", r"jogurt", r"zmrzlin", r"kase", r"musli", r"cereal", r"croissant", r"donut", r"pudink", r"dort", r"sirup", r"poleva na", r"\bkrem\b", r"pomazank", r"napln"]),
    ("bonbony", "Bonbony a žvýkačky", "bonbony", "sladkosti-a-snacky", [r"bonbon", r"zele\b", r"\bzelé", r"haribo", r"lentilk", r"zvykack", r"lizatk", r"\bmentos", r"tic tac", r"dropsy"], []),
    ("susenky", "Sušenky a oplatky", "sušenky", "sladkosti-a-snacky", [r"susenk", r"oplatk", r"keks", r"perniky?\b", r"perni[cč]", r"\bopavia", r"\bbebe\b", r"tatranky", r"horalky", r"miladin", r"cracker", r"vafl", r"piskot", r"cukrov"], []),
    ("chipsy-a-snacky", "Chipsy a slané snacky", "chipsy", "sladkosti-a-snacky", [r"chips", r"brambur[uů]?ky", r"tortill", r"pringles", r"\bbake rolls", r"krekr", r"tycinky slane", r"popcorn", r"nachos", r"arasid", r"pistaci", r"kesu", r"mandle", r"orech", r"oriesk", r"smes orech"], [r"cokolad"]),
    # --- mléčné
    ("vejce", "Vejce", "vejce", "mlecne-vyrobky-a-vejce", [r"\bvejce\b"], [r"cokolad", r"kinder", r"vajick"]),
    ("mleko", "Mléko", "mléko", "mlecne-vyrobky-a-vejce", [r"\bmleko\b", r"trvanlive mleko", r"cerstve mleko", r"mleko polotucne", r"mleko plnotucne"], [r"cokolad", r"kokos", r"rostlin", r"ovesn", r"mandlov", r"sojov", r"kondenz", r"tela", r"pletov", r"cistic", r"susen", r"nivea", r"telov", r"odlicov", r"opalov"]),
    ("maslo", "Máslo", "máslo", "mlecne-vyrobky-a-vejce", [r"\bmaslo\b", r"\bmasla\b", r"ghi\b", r"\bghee\b"], [r"arasid", r"kakaov", r"bambuck", r"tel", r"rostlinn", r"pecivo", r"croissant", r"susenk", r"bylinkov.*bageta"]),
    ("syr", "Sýry", "sýr", "mlecne-vyrobky-a-vejce", [r"\bsyr", r"eidam", r"gouda", r"mozzarel", r"\bfeta\b", r"hermelin", r"niva", r"parmez", r"cheddar", r"tavene", r"\blucina", r"camembert", r"brie\b", r"\bjihocesk[ya] syrecek", r"tvaruzk", r"emental", r"madeta.*plat", r"zottarella", r"\bhalloumi", r"ricott", r"mascarpone", r"\bsyrecek", r"babybel", r"vesela krava", r"krolewski", r"smetanito", r"apetito", r"\bgervais", r"\bcottage", r"\balmette", r"\bmeggle", r"\bpresident\b", r"\bhochland", r"\bphiladelphia", r"\blaktos", r"t\. ?v\. ?s", r"\bzerve", r"parenic", r"korbac"], [r"chips", r"pizza", r"susen", r"krekr", r"omacka", r"bageta", r"chleb", r"rohlik"]),
    ("smetana", "Smetana", "smetanu", "mlecne-vyrobky-a-vejce", [r"smetan", r"slehack", r"zakys"], [r"zmrzlin", r"jogurt", r"tvaroh", r"susen", r"dort"]),
    ("tvaroh", "Tvaroh", "tvaroh", "mlecne-vyrobky-a-vejce", [r"tvaroh", r"cottage", r"\bskyr\b"], [r"dezert s", r"kolac", r"buchta", r"stavnat"]),
    ("jogurt", "Jogurty a mléčné dezerty", "jogurty", "mlecne-vyrobky-a-vejce", [r"jogurt", r"activia", r"\bactimel", r"kefir", r"pudink", r"\bdanette", r"\bmonte\b", r"lipanek", r"\bathos", r"zott", r"\bjogobell", r"\bolma\b", r"pribinacek", r"\bkunin", r"\bfantasia\b", r"\bpierot", r"\bmuller\b"], [r"zmrzlin", r"pleťov", r"cokolad.*tycin"]),
    ("rostlinne-alternativy", "Rostlinné alternativy", "rostlinné nápoje", "mlecne-vyrobky-a-vejce", [r"rostlinn", r"ovesn[yý] napoj", r"sojov[yý] napoj", r"mandlov[yý] napoj", r"\balpro"], []),
    # --- maso
    ("kava", "Káva", "kávu", "kava-a-caj", [r"\bkava\b", r"\bkavy\b", r"espresso", r"cappuccino", r"\bjacobs", r"tchibo", r"nescafe", r"lavazza", r"\bdouwe", r"\bdallmayr", r"kavov", r"kavove kapsle", r"\bdolce gusto", r"\bjihlavank", r"\beduscho", r"\bmelta\b", r"\brocca\b", r"mleta kava", r"prazen", r"\bl.?or\b", r"tassimo", r"starbucks", r"\bkapsle\b(?!.*(?:prani|pračk|myc|persil|ariel|lenor|jar\b|somat|finish|tablet))", r"kafe\b", r"barista", r"zrnkov"], [r"kavovar", r"mlynek", r"hrnek", r"salek", r"zmrzlin", r"cokolad", r"sirup", r"persil", r"ariel", r"lenor", r"\bjar\b", r"somat", r"finish", r"prani", r"mycky", r"tablet"]),
    ("caj", "Čaj", "čaj", "kava-a-caj", [r"\bcaj\b", r"\bcaje\b", r"\bteekanne", r"\bpickwick", r"\bmilford", r"\bbylinny"], [r"ledovy", r"ice tea", r"nestea", r"svicka"]),
    ("pivo", "Pivo", "pivo", "pivo-a-vino", [r"\bpivo\b", r"lezak", r"\bpilsner", r"\bgambrinus", r"\bkozel", r"\bstaropramen", r"budvar", r"\bradegast", r"\bkrusovic", r"\bbernard\b", r"\bbirell", r"\bsvijan", r"\bostravar", r"\bbranik", r"\bplzen", r"\bheineken", r"\brebel\b", r"\bzubr\b", r"\blobkowicz", r"\bholba", r"\bprimator", r"\bvelkopopovick", r"\bpivni", r"\bipa\b", r"\bnealko pivo", r"radler", r"\bbazant", r"zlatopramen", r"\bexcelent\b", r"\bmustang\b", r"svijansk", r"starobrno", r"\blitovel", r"cerna hora", r"\bchotebor", r"\bpardal", r"\bhubertus", r"\bpatron\b", r"\bmaz\b", r"\bbrezn", r"remesln[aá] piv", r"\bpivovar"], [r"sklenic", r"tacky", r"\bsyr", r"chleb", r"pivni.*tycink"]),
    ("vino", "Víno", "víno", "pivo-a-vino", [r"\bvino\b", r"\bvina\b", r"sekt", r"prosecco", r"\bbohemia sekt", r"frankovk", r"ryzlink", r"veltlin", r"chardonnay", r"merlot", r"sauvignon", r"cabernet", r"rulandsk", r"muskat", r"\bmoravsk[eé] zemsk", r"svatomartinsk", r"champagne", r"sampansk", r"rose\b", r"primitivo", r"\bcava\b", r"vinarstv", r"\bsklep", r"\bvalley\b", r"\bbzenec", r"habansk", r"modry portugal", r"zweigelt", r"svatovavrinec", r"\bpinot", r"\btramin", r"muller ?thurgau", r"\bpalava", r"\bfrizzante", r"\bspumante", r"svarak", r"\bkatz\b"], [r"ocet", r"vinny ocet", r"vino ?grep", r"hrozn", r"sklenic", r"vinea"]),
    ("vodka", "Vodka", "vodku", "alkohol", [r"vodk", r"\bsmirnoff", r"absolut\b", r"\bfinlandia", r"\bamundsen", r"\bnemiroff"], []),
    ("rum", "Rum a tuzemák", "rum", "alkohol", [r"\brum\b", r"tuzemak", r"\bcaptain morgan", r"\bbozkov\b(?!.*vodk)", r"bacardi", r"\bjindrichohradeck", r"\bspiced", r"\bhavana club", r"don papa", r"\brepublica\b", r"diplomatico", r"\bbumbu", r"legendario", r"\bdictador", r"\bzacapa"], []),
    ("gin", "Gin", "gin", "alkohol", [r"\bgin\b", r"\bgordon", r"\bbeefeater", r"\bbombay", r"\bjohnny ?ruth"], []),
    ("whisky", "Whisky a brandy", "whisky", "alkohol", [r"whisk(?:y|ey)", r"bourbon", r"\bjameson", r"\bjack daniel", r"\bballantine", r"\btullamore", r"\bbrandy", r"\bkoniak", r"cognac", r"\bmetaxa"], []),
    ("likery-a-destilaty", "Likéry a destiláty", "likéry", "alkohol", [r"liker", r"\bbecherovka", r"\bjagermeister", r"\bfernet", r"slivovic", r"hruskovic", r"merunkovic", r"\bdestilat", r"\bbaileys", r"\bteq?uil", r"\bpalenk", r"vajecny liker", r"\bberentzen", r"\bstroh", r"\bjelinek", r"\bdzin"], [r"bonbon", r"pralink", r"cokolad"]),
    ("nealko", "Nealko nápoje", "nealko nápoje", "nealko-napoje", [r"minerál", r"mineraln", r"limonad", r"\bcola\b", r"coca", r"pepsi", r"\bsprite", r"\bfanta\b", r"capri-?sun", r"schweppes", r"\btarga\b", r"royal crown", r"\bnektar", r"\bstava\b", r"100 ?% (?:jablko|pomeranc)", r"\bmattoni", r"magnesia", r"\bdobra voda", r"\bkofola", r"\brajec", r"\bpodebradk", r"\bdzus", r"\bdzusy", r"\bdzusu", r"\bmost\b", r"\bsirup", r"\bsodovk", r"\btonic", r"energeticky", r"\bred bull", r"\bmonster\b", r"\bbig shock", r"\bricola\b", r"\bnestea", r"ledovy caj", r"ice tea", r"\bcappy", r"\brauch", r"\bhello\b", r"\bvoda\b", r"\bvody\b", r"\bperliva", r"\bneperliv", r"\bkoncentrat", r"\bnapoj"], [r"toaletni", r"micelarni", r"toaletni voda", r"parfem", r"\bvlasov", r"ustni voda", r"\bkrem", r"\bmleko", r"jogurt", r"ovesn", r"mandlov", r"sojov", r"kokosov", r"rostlin", r"protein", r"plnic", r"cistic"]),
    ("kureci-maso", "Kuřecí maso", "kuřecí maso", "maso-a-ryby", [r"kurec", r"kure\b", r"\bkure ", r"kuřat", r"kurat", r"drubez", r"krut"], [r"salam", r"sunk", r"park", r"klobas", r"polevk", r"vyvar", r"krmivo", r"kocky", r"psy", r"pastika", r"chips"]),
    ("veprove-maso", "Vepřové maso", "vepřové maso", "maso-a-ryby", [r"veprov", r"krkovic", r"\bbok\b", r"panenk", r"\bplec\b", r"kotlet", r"vepr"], [r"salam", r"sunk", r"park", r"klobas", r"pastik", r"konzerv", r"kocky", r"psy", r"sadlo", r"skvarky"]),
    ("hovezi-maso", "Hovězí maso", "hovězí maso", "maso-a-ryby", [r"hovez", r"\bsteak", r"rostenec", r"svickov"], [r"salam", r"vyvar", r"polevk", r"bujon", r"psy", r"kocky", r"konzerv"]),
    ("mlete-maso", "Mleté maso", "mleté maso", "maso-a-ryby", [r"mlete maso", r"mlete veprov", r"mlete hovez", r"mlete kurec", r"burger"], [r"kav", r"pepr", r"koreni"]),
    ("ryby", "Ryby a mořské plody", "ryby", "maso-a-ryby", [r"\bkapr", r"losos", r"tunak", r"\btresk", r"pstruh", r"makrel", r"sled", r"krevet", r"ryb[ayi]\b", r"filet", r"sardin", r"\bsurimi", r"rybi"], [r"kocky", r"psy", r"krmivo"]),
    # --- uzeniny
    ("parky-a-klobasy", "Párky a klobásy", "párky", "uzeniny-a-lahudky", [r"park", r"klobas", r"spekacky", r"spekack", r"vursty", r"jitrnic", r"jelit"], []),
    ("salam-a-sunka", "Salámy a šunky", "salám a šunku", "uzeniny-a-lahudky", [r"salam", r"sunk", r"slanina", r"kabanos", r"uherak", r"\bfuet\b", r"\bjamon", r"\bcoppa\b", r"kladensk", r"debrecinsk", r"\bvysocina", r"\bpolican", r"\bmortadel", r"prosciutto", r"serrano", r"chorizo", r"uzene maso", r"\buzen"], [r"pizza", r"bageta"]),
    ("lahudky", "Lahůdky a pomazánky", "lahůdky", "uzeniny-a-lahudky", [r"pomazank", r"salat", r"pastik", r"hummus", r"chlebicek", r"obloz", r"\bsushi", r"aspik", r"tlacenk", r"utopenc"], [r"okurk", r"hlavkov", r"ledovy"]),
    # --- pečivo
    ("chleb-a-pecivo", "Chléb a pečivo", "pečivo", "pecivo", [r"chleb", r"rohlik", r"bageta", r"kaiserk", r"veka\b", r"houska", r"croissant", r"\bkobliha", r"kolac", r"buchta", r"bochnik", r"\btoust", r"pecivo", r"loupak", r"vanock", r"\bdonut", r"tastick", r"pletynk"], [r"strouhank", r"krekr"]),
    # --- trvanlivé
    ("cukr", "Cukr", "cukr", "trvanlive-potraviny", [r"\bcukr\b", r"cukr moucka", r"cukr krupice", r"cukr krystal", r"trtinovy cukr", r"kokosovy cukr"], [r"bez cukru", r"cukrov", r"cukrar"]),
    ("mouka", "Mouka", "mouku", "trvanlive-potraviny", [r"mouk"], []),
    ("olej", "Olej a tuky", "olej", "trvanlive-potraviny", [r"\bolej", r"\boliv[ay]? olej", r"repkov", r"slunecnicov[yý] olej", r"\bhera\b", r"\brama\b", r"margarin", r"\bflora\b", r"\bperla\b", r"\bsadlo\b", r"\btuk na"], [r"motorov", r"masazni", r"telov", r"tunak", r"sardin", r"v oleji", r"rajcata v"]),
    ("testoviny", "Těstoviny", "těstoviny", "trvanlive-potraviny", [r"testovin", r"spaget", r"\bpenne\b", r"fusilli", r"\bnudle", r"lasagn", r"tortellin", r"\bgnocchi", r"\bpanzani", r"barilla", r"\bkolinska"], [r"polevk", r"hotov"]),
    ("ryze-a-lusteniny", "Rýže a luštěniny", "rýži", "trvanlive-potraviny", [r"\bryze", r"cocka", r"fazol", r"hrach\b", r"hrasek", r"cizrna", r"kuskus", r"bulgur", r"quinoa"], [r"mrazen", r"chlebicek", r"chips"]),
    ("konzervy", "Konzervy a hotová jídla", "konzervy", "trvanlive-potraviny", [r"konzerv", r"kompot", r"\bhotov", r"polevk", r"\bbujon", r"omack", r"kecup", r"horcice", r"majonez", r"tatarsk", r"dresink", r"okurk", r"olivy", r"rajcatov", r"protlak", r"sterilovan", r"pastik", r"kysane zeli"], [r"kocky", r"psy"]),
    ("snidane", "Cereálie, müsli a džemy", "cereálie", "trvanlive-potraviny", [r"cereal", r"musli", r"mysli", r"\bovesn[eé] vlocky", r"vlocky", r"dzem", r"marmelad", r"\bmed\b", r"nutella", r"lisk.*krem", r"granol", r"\bkase\b", r"ovesna kase"], []),
    # --- mražené
    ("mrazena-pizza", "Mražená pizza", "mraženou pizzu", "mrazene-potraviny", [r"pizza", r"\bpizz"], [r"kecup", r"omacka", r"koreni", r"pec na", r"sul"]),
    ("zmrzlina", "Zmrzlina", "zmrzlinu", "mrazene-potraviny", [r"zmrzlin", r"\bmagnum", r"\bcornetto", r"nanuk", r"\bmrozn", r"ice cream"], []),
    ("mrazene", "Mražené potraviny", "mražené potraviny", "mrazene-potraviny", [r"mrazen", r"hranolk", r"\bpangas", r"\bknedl"], []),
    # --- ovoce/zelenina
    ("koreni-a-peceni", "Koření a pečení", "potřeby na pečení", "trvanlive-potraviny", [r"koreni", r"\bpepr", r"\bsul\b", r"prasek do peciva", r"drozdi", r"vanilk", r"\bkakao\b", r"kakaov[yý] prasek", r"poleva", r"strouhank", r"\bdr\.? oetker", r"\bvitana", r"\bkotanyi", r"\bdroz"], []),
    ("banany", "Banány", "banány", "ovoce-a-zelenina", [r"banan"], [r"cokolad", r"susen", r"jogurt", r"chips", r"pyre", r"kapsick", r"napoj"]),
    ("jablka-a-hrusky", "Jablka a hrušky", "jablka", "ovoce-a-zelenina", [r"jablk", r"hrusk"], [r"dzus", r"mosty", r"most\b", r"napoj", r"jogurt", r"cider", r"ocet", r"kapsick", r"strudl", r"chips", r"lahev", r"susen", r"pyre", r"\bkoncentrat"]),
    ("brambory", "Brambory", "brambory", "ovoce-a-zelenina", [r"brambor"], [r"chips", r"hranolk", r"lupinky", r"krokety", r"knedl", r"bramburky", r"kase", r"salat", r"placky", r"bramborak", r"snack", r"\bchio\b", r"pom-?bar"]),
    ("rajcata-a-papriky", "Rajčata a papriky", "rajčata a papriky", "ovoce-a-zelenina", [r"rajcat", r"paprik", r"cherry"], [r"protlak", r"kecup", r"omack", r"koreni", r"susen", r"chips", r"pasta", r"loupan", r"krajen", r"sterilov", r"salam", r"klobas", r"v oleji", r"pyre"]),
    ("ovoce", "Ovoce", "ovoce", "ovoce-a-zelenina", [r"mandarin", r"pomeranc", r"citron", r"hrozn", r"kiwi", r"ananas", r"jahod", r"boruvk", r"malin", r"mango", r"avokad", r"granaty", r"grep", r"\bovoce\b", r"klementin", r"svestk", r"broskv", r"melou?n", r"limet", r"datl", r"fik[yu]"], [r"dzus", r"napoj", r"jogurt", r"cokolad", r"dzem", r"susen", r"caj", r"zmrzlin", r"sirup", r"limonad", r"bonbon", r"zele"]),
    ("zelenina", "Zelenina", "zeleninu", "ovoce-a-zelenina", [r"cibul", r"cesnek", r"mrkev", r"okurka salat", r"salatova okurka", r"okurka hadovk", r"hlavkov", r"ledovy salat", r"zeli\b", r"kvetak", r"brokolic", r"cuketa", r"\bdyne\b", r"redkvick", r"celer", r"porek", r"zampion", r"houby", r"\bzelenina\b", r"spenat", r"salat ledovy"], [r"kysane", r"sterilov", r"mrazen", r"polevk"]),
    # --- nápoje
    # --- drogerie a kosmetika
    ("toaletni-papir", "Toaletní papír a ubrousky", "toaletní papír", "drogerie", [r"toaletni papir", r"\btoal\. papir", r"papirove? kapesnik", r"kuchynsk[eé] utierk", r"papirove utierky", r"\bubrousk", r"\bzewa\b", r"\blinteo\b", r"\bharmony\b", r"\bperlenka", r"\bvelvet\b", r"\bregina\b"], [r"vlhcen", r"detsk"]),
    ("praci-prostredky", "Prací prostředky a aviváže", "prací prostředky", "drogerie", [r"praci", r"prasek na prani", r"gel na prani", r"kapsle na prani", r"avivaz", r"\bariel", r"\bpersil", r"\bjar\b(?=.*prani)", r"\bLenor", r"\blenor", r"\bcoccolino", r"\bsilan", r"\bvanish", r"\bwoolite", r"\bperwoll", r"\bformil", r"\bclin\b(?=.*prani)", r"\bdash\b", r"\bpraci"], [r"pracka", r"susak", r"stojan"]),
    ("myti-nadobi-a-uklid", "Mytí nádobí a úklid", "čisticí prostředky", "drogerie", [r"mycku", r"do mycky", r"\bjar\b", r"\bpur\b", r"\bfinish\b", r"\bsomat", r"cistic", r"\bsavo\b", r"\bdomestos", r"\bduck\b", r"\bbref\b", r"wc blok", r"\bdixan", r"\bcif\b", r"\bfrosch", r"\bmr\.? proper", r"\bsavo", r"\bprostredek na", r"\bosvezovac", r"\bair wick", r"\bglade\b", r"\bambi pur", r"\bhoubicky", r"\bhadr"], []),
    ("kosmetika", "Kosmetika a hygiena", "kosmetiku", "kosmetika", [r"sampon", r"kondicion", r"sprchov", r"\bmydlo", r"zubni past", r"zubni kartac", r"ustni vod", r"deodorant", r"antiperspir", r"\bkrem\b", r"\bkrem na", r"telov", r"pletov", r"\bnivea", r"\bdove\b", r"\bpalmolive", r"\bcolgate", r"\bsignal\b", r"\blacalut", r"\bgarnier", r"\blistrine", r"\blisterine", r"\bgillette", r"\bholic", r"\bvlozky", r"\btampon", r"\bodlicovac", r"\bvatov", r"micelarni", r"\bparfem", r"toaletni voda", r"\bbalzam", r"\blak na vlasy", r"\bbarva na vlasy", r"\bvlasov", r"\bcorega", r"\bsensodyne", r"\bparodontax", r"\bduschi", r"\bfa\b", r"\bfructis", r"\bheadshoulders", r"head ?& ?shoulders", r"\bramses", r"\bdermacol"], [r"\bvlasy\b.*zastrih", r"kulma", r"fen\b", r"zehlicka"]),
    ("pleny-a-detska-vyziva", "Pleny a dětská výživa", "pleny", "pro-deti", [r"\bplen", r"\bpampers", r"\bhuggies", r"detsk[aá] vyziv", r"kojenecke", r"\bhami\b", r"\bsunar\b", r"\bnutrilon", r"vlhcene ubrousky", r"\bkapsick[ay] ovocn", r"ovocna kapsick", r"\bkapsicka\b"], [r"kocky", r"psy"]),
    ("krmivo-pro-kocky", "Krmivo pro kočky", "krmivo pro kočky", "mazlicci", [r"pro kock", r"\bwhiskas", r"\bfelix\b", r"\bsheba", r"\bkitekat", r"\bgourmet\b", r"\bperfect fit\b.*cat", r"\bpurina.*kock", r"\bpropesko.*kock", r"\bkocici", r"\bkocka", r"\bstelivo"], []),
    ("krmivo-pro-psy", "Krmivo pro psy", "krmivo pro psy", "mazlicci", [r"pro psy", r"\bpedigree", r"\bchappi", r"\bfrolic", r"\bpsi\b", r"\bpsi ", r"\bpurina.*psy", r"\bdentastix", r"\bpro psa"], []),
    # --- nepotraviny (hlavně Lidl web, Norma, Kaufland)
    ("hracky", "Hračky a hry", "hračky", "hracky", [r"hrack", r"\blego\b", r"stavebnic", r"puzzle", r"panenk", r"plysov", r"spolecensk[aá] hra", r"deskov[aá] hra", r"\bautickov?", r"autodrah", r"omalovank", r"\bkostky\b", r"vanocni hrack"], []),
    ("obleceni-a-obuv", "Oblečení a obuv", "oblečení", "obleceni", [r"triko", r"tricko", r"\bmikina", r"\bsvetr", r"kalhot", r"\bdziny", r"legin", r"\bbunda", r"\bkabat", r"pyzam", r"ponozk", r"puncoch", r"\bboxerk", r"kalhotk", r"podprsenk", r"spodni pradlo", r"\bbody\b", r"\bsaty\b", r"\bobuv", r"\bboty\b", r"pantofl", r"\btenisk", r"\bcepice", r"\brukavice", r"\bsala\b", r"\bnakrcnik", r"overal", r"teplak"], [r"rukavice na mytí", r"kuchynsk"]),
    ("elektro", "Elektro a spotřebiče", "elektro", "elektro", [r"\bmixer", r"kavovar", r"\bvysavac", r"\bfen\b", r"\bkulma", r"zehlick", r"rychlovarn", r"\bfritez", r"\bgril\b", r"kontaktni gril", r"toustovac", r"\bpowerbank", r"sluchatk", r"reproduktor", r"\bnotebook", r"\bmonitor", r"\btelevizor", r"\bprojektor", r"\bnabijec", r"\bzarovk", r"\bled\b", r"\bbaterie\b", r"\bzastrihovac", r"\bholici strojek", r"\bzubni kartacek elektr", r"\belektrick", r"\bkamera", r"\bvysilack", r"\bodvlhcovac", r"\bpecici trouba", r"\bmikrovln", r"\bvarna konvice", r"\brobot\b", r"\bkuchynsky robot", r"\bvahy\b", r"\bosvetleni"], []),
    ("domacnost-a-kuchyne", "Domácnost a kuchyně", "potřeby do domácnosti", "domacnost", [r"\bpanev", r"\bhrnec", r"\bnadobi", r"\btalir", r"\bhrnek", r"\bsklenic", r"\bpribor", r"\bnuz\b", r"\bnoze\b", r"\bdoz[ay]\b", r"\bkrabic", r"\bufon", r"\bvalec", r"\bplech", r"\bforma na", r"\bstrouhadl", r"\bprkenk", r"\bpovleceni", r"\bpovlak", r"\bdeka\b", r"\bpled", r"\bpolstar", r"\bprosteradl", r"\bruc?nik", r"\bosusk", r"\bzaves", r"\bkoberec", r"\bsvick", r"\bdekorac", r"\bvanocni ozdob", r"\bvanocni stromek", r"\bvanocni osvetl", r"\bstul\b", r"\bzidl", r"\bnabytek", r"\bkreslo", r"\bpolic", r"\bsuper ?cena.*dekor", r"\bmatrace"], []),
    ("dilna-a-zahrada", "Dílna, nářadí a zahrada", "nářadí", "dum-a-zahrada", [r"\bvrtac", r"\bsroubovak", r"\bpila\b", r"\bpily\b", r"\bbruska", r"\bnaradi", r"\bkufr s", r"\bklic[ue]?\b", r"\bkladivo", r"\bpajk", r"\bsvarec", r"\bzahradn", r"\bhadice", r"\bsekack", r"\bkompresor", r"\bzebrik", r"\bmetr\b", r"\bvodovah", r"\bparkside", r"\baku\b", r"\bsprchov", r"\bbaterie umyvadl", r"\bautosedack", r"\bdo auta", r"\bautomobil", r"\bsnehova lopata", r"\bposyp", r"\bkrmitko", r"\bptaci"], []),
    ("sport", "Sport a volný čas", "sportovní potřeby", "sport", [r"\bfitness", r"\bcinky", r"\bpodlozka na cvic", r"\brotoped", r"\btrenazer", r"\bkolo\b", r"\bkolobezk", r"\blyze", r"\bbrusle", r"\bstan\b", r"\bspacak", r"\btermosk", r"\bbatoh", r"\bkufr\b", r"\bcestovni", r"\bdalekohled", r"\bsportovni", r"\bpadel", r"\braket", r"\bmic\b"], []),
]

TYPES = [{"slug": t[0], "nazev": t[1], "h": t[2], "kategorie": t[3],
          "inc": [re.compile(x) for x in t[4]], "exc": [re.compile(x) for x in t[5]]} for t in T]
TYPE_BY_SLUG = {t["slug"]: t for t in TYPES}

# Lidl web gives its own category path for non-food — map the top segments
LIDL_PATH = [
    ("Hračky", "hracky"), ("Móda", "obleceni-a-obuv"), ("Multimédia", "elektro"), ("Malé domácí spotřebiče", "elektro"),
    ("Vlasová kosmetika", "elektro"), ("Masáže a relaxace", "elektro"), ("Zdraví a krása", "kosmetika"),
    ("Domácnost a kuchyně", "domacnost-a-kuchyne"), ("Bydlení a vybavení", "domacnost-a-kuchyne"),
    ("Dům a zahrada", "dilna-a-zahrada"), ("Sport a volný čas", "sport"), ("Dětský svět", "hracky"),
    ("Knihy a média", "hracky"), ("Potraviny a drogerie", None),
]


def classify(title: str, extra: str = "", chain_path: str | None = None) -> str | None:
    """Product type slug for an offer title (None = unknown -> only in the chain listing)."""
    if chain_path:
        for key, slug in LIDL_PATH:
            if key in chain_path and slug:
                # appliances inside "Zdraví a krása" (hair dryers, shavers) are elektro, the rest cosmetics
                return slug
    t = norm(title)
    for ty in TYPES:
        if any(rx.search(t) for rx in ty["inc"]) and not any(rx.search(t) for rx in ty["exc"]):
            return ty["slug"]
    if extra:
        t2 = norm(title + " " + extra)
        for ty in TYPES:
            if any(rx.search(t2) for rx in ty["inc"]) and not any(rx.search(t2) for rx in ty["exc"]):
                return ty["slug"]
    return None


# Brands for "<type> <brand>" product pages. Only well-known FMCG brands (a wrong brand page is worse than none).
BRANDS = """
Milka Orion Lindt Ritter Sport Kinder Ferrero Raffaello Merci Toblerone Figaro Studentská Toffifee Mars Snickers Twix Bounty KitKat Kit Kat
Haribo Lentilky Mentos Opavia Tatranky Horalky Fidorka Kofila Margot Deli Bebe Pringles Bake Rolls Chio Lay's Doritos Tuc Brumík
Jacobs Tchibo Nescafé Lavazza Douwe Egberts Dallmayr Café Royal Segafredo Davidoff Illy Dolce Gusto Teekanne Pickwick Milford Lipton
Pilsner Urquell Gambrinus Kozel Velkopopovický Kozel Staropramen Budweiser Budvar Radegast Krušovice Bernard Birell Svijany Ostravar Braník Heineken Rebel Zubr Lobkowicz Holba Primátor Starobrno Plzeň
Bohemia Sekt Božkov Jindřichohradecký Captain Morgan Bacardi Absolut Smirnoff Finlandia Amundsen Becherovka Jägermeister Fernet Stock Jameson Jack Daniel's Ballantine's Tullamore Gordon's Beefeater Bombay Metaxa Baileys
Coca-Cola Pepsi Sprite Fanta Mattoni Magnesia Dobrá voda Kofola Rajec Poděbradka Red Bull Monster Big Shock Relax Hello Rauch Cappy Toma Pfanner Rioba Hello
Danone Activia Actimel Danette Pilos Olma Madeta Kunín Hollandia Zott Zottarella Gervais Lipánek Pribináček Lučina Apetito Président Hochland Almette Philadelphia Alpro Milbona Tatra Ehrmann Müller Bonduelle Hamé Giana Franz Josef Hellmann's Heinz Kand Spak Vitana Podravka Dr. Oetker Panzani Barilla Kolínská Babiččina volba Ceria Hera Rama Flora Perla
Kostelecké Krahulík Le & Co Vysočina Poličan Herkules Madeland Tulip Váhala Steinhauser Kmotr Penam
Persil Ariel Lenor Coccolino Silan Vanish Woolite Perwoll Jar Pur Finish Somat Savo Domestos Duck Bref Cif Frosch Mr. Proper Air Wick Glade Ambi Pur Zewa Linteo Harmony Velvet Regina Tempo Perlenka
Nivea Dove Palmolive Colgate Signal Lacalut Garnier Fructis Elseve Listerine Gillette Head & Shoulders Rexona Fa Old Spice Axe Schauma Syoss Corega Sensodyne Parodontax Elmex Duschi Dermacol Bioderma Neutrogena Vichy
Pampers Huggies Hami Sunar Nutrilon Bebivita Hipp
Whiskas Felix Sheba Kitekat Gourmet Perfect Fit Purina Pedigree Chappi Frolic Propesko Brit Dentastix
Parkside Silvercrest Livarno Esmara Livergy Crivit Lupilu Ernesto Tefal Philips Bosch Rowenta Braun Remington Sencor ETA Concept Nutribullet
""".split("\n")


def _brand_list():
    # multi-word brands are written as they appear; split lines on 2+ spaces is overkill — we keep a curated list
    words = " ".join(BRANDS)
    known = ["Ritter Sport", "Kit Kat", "Bake Rolls", "Lay's", "Douwe Egberts", "Café Royal", "Dolce Gusto", "Pilsner Urquell",
             "Velkopopovický Kozel", "Bohemia Sekt", "Captain Morgan", "Jack Daniel's", "Coca-Cola", "Dobrá voda", "Red Bull",
             "Big Shock", "Franz Josef", "Dr. Oetker", "Babiččina volba", "Le & Co", "Mr. Proper", "Air Wick", "Ambi Pur",
             "Head & Shoulders", "Old Spice", "Perfect Fit", "Hellmann's", "Gordon's", "Ballantine's"]
    multi_first = {k.split()[0] for k in known}
    single = [w for w in words.split() if w not in multi_first and len(w) > 1 and w not in ("&", "Co", "voda", "Sport", "Kat", "Rolls",
              "Urquell", "Kozel", "Sekt", "Morgan", "Daniel's", "Egberts", "Royal", "Gusto", "Bull", "Shock", "Josef", "Oetker",
              "volba", "Proper", "Wick", "Pur", "Shoulders", "Spice", "Fit", "Dobrá", "Babiččina")]
    return sorted(set(known) | set(single) | {"Kozel", "Budvar"}, key=len, reverse=True)


BRAND_LIST = _brand_list()
_BRX = [(b, re.compile(r"(?<![a-z0-9])" + re.escape(norm(b)) + r"(?![a-z0-9])")) for b in BRAND_LIST]


def brand(title: str) -> str | None:
    t = norm(title)
    best = None
    for b, rx in _BRX:
        m = rx.search(t)
        if m and (best is None or m.start() < best[1]):
            best = (b, m.start())
    return BRAND_ALIAS.get(best[0], best[0]) if best else None


# one brand under several names -> one product page
BRAND_ALIAS = {"Kozel": "Velkopopovický Kozel", "Budweiser": "Budweiser Budvar", "Budvar": "Budweiser Budvar", "KitKat": "Kit Kat",
               "Zottarella": "Zott", "Kofila": "Orion", "Margot": "Orion", "Studentská": "Orion", "Fidorka": "Opavia", "Tatranky": "Opavia",
               "Horalky": "Sedita", "Raffaello": "Ferrero", "Cien Beauty": "Cien", "Dobrá voda": "Dobrá voda"}
