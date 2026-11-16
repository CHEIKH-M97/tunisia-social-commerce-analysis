"""Normalize free-text governorate labels to Tunisia's 24 official governorates.

Layers, in order (each label is resolved by the first layer that succeeds):
  1. exact   - cleaned label equals a governorate name or a known alias
  2. city    - cleaned label equals a known city / delegation name
  3. fuzzy   - close spelling match (difflib ratio >= 0.85), for typos
  4. contains- label contains exactly one governorate / city name as whole words
  5. address - (row level, only for labels still unresolved) the address
               contains exactly one governorate / city name
Anything else -> "Unknown".
"""
from __future__ import annotations

import difflib
import re
import unicodedata

UNKNOWN = "Unknown"

# Canonical names (ASCII, as in the source data) -> extra spellings / aliases
GOVERNORATES: dict[str, list[str]] = {
    "Tunis": ["grand tunis", "tunis ville"],
    "Ariana": ["aryana", "ariena"],
    "Ben Arous": ["benarous", "ben arouse", "ben arous", "bn arous"],
    "Manouba": ["mannouba", "la manouba", "manuba"],
    "Nabeul": ["nabel", "nabeull", "nabul", "cap bon"],
    "Zaghouan": ["zaghwan", "zagouan"],
    "Bizerte": ["bizert", "benzart", "binzart"],
    "Beja": ["bja"],
    "Jendouba": ["jandouba", "jendoub"],
    "Kef": ["le kef", "el kef", "kaf", "al kef"],
    "Siliana": ["seliana", "silyana"],
    "Sousse": ["sous", "souse", "soussa"],
    "Monastir": ["mounastir", "monastire"],
    "Mahdia": ["mehdia", "mahdiya"],
    "Sfax": ["sfaks", "safakes", "sfakes"],
    "Kairouan": ["kairaouan", "kairawan", "qairouan", "kirouan"],
    "Kasserine": ["kasrine", "kassrine", "gasserine", "kasserin"],
    "Sidi Bouzid": ["sidi bou zid", "sidibouzid", "sidi bouzaid"],
    "Gabes": ["gabs", "qabes", "gabis"],
    "Medenine": ["mednine", "medenin", "madanine"],
    "Tataouine": ["tatouine", "tataouin", "tatawin"],
    "Gafsa": ["gafssa", "kafsa"],
    "Tozeur": ["touzeur", "tozer"],
    "Kebili": ["kbili", "qebili", "gbili"],
}

# Main cities / delegations -> governorate. Deliberately excludes names that
# exist in more than one governorate (e.g. El Hamma, Chebika, Medina, El Ksar).
CITIES: dict[str, list[str]] = {
    "Tunis": ["la marsa", "marsa", "carthage", "le bardo", "bardo", "la goulette", "goulette",
              "sidi bou said", "el omrane", "ettahrir", "sijoumi", "sidi hassine", "kabaria",
              "ezzouhour", "el ouardia", "bab souika", "jebel jelloud", "berges du lac", "el menzah"],
    "Ariana": ["ennasr", "raoued", "soukra", "la soukra", "kalaat el andalous", "sidi thabet",
               "ettadhamen", "mnihla", "borj louzir", "chotrana", "ghazela", "riadh el andalous"],
    "Ben Arous": ["rades", "megrine", "ezzahra", "hammam lif", "hammam chott", "boumhel", "bou mhel",
                  "el mourouj", "mourouj", "mornag", "fouchana", "mohamedia", "medina jedida",
                  "nouvelle medina"],
    "Manouba": ["den den", "douar hicher", "oued ellil", "mornaguia", "tebourba", "borj el amri",
                "jedaida", "el batan"],
    "Nabeul": ["hammamet", "korba", "kelibia", "menzel temime", "grombalia", "soliman",
               "beni khalled", "dar chaabane", "bou argoub", "menzel bouzelfa", "takelsa",
               "el haouaria", "hammam ghezaz", "beni khiar", "el mida"],
    "Zaghouan": ["el fahs", "fahs", "nadhour", "zriba", "bir mcherga", "saouaf"],
    "Bizerte": ["menzel bourguiba", "mateur", "ras jebel", "menzel jemil", "el alia", "sejnane",
                "ghar el melh", "utique", "tinja", "joumine", "menzel abderrahmane"],
    "Beja": ["medjez el bab", "mejez el bab", "testour", "nefza", "teboursouk", "amdoun",
             "goubellat", "thibar"],
    "Jendouba": ["tabarka", "ain draham", "bou salem", "ghardimaou", "fernana", "oued meliz", "balta"],
    "Kef": ["dahmani", "tajerouine", "sakiet sidi youssef", "kalaat senan", "nebeur", "jerissa"],
    "Siliana": ["makthar", "maktar", "gaafour", "bou arada", "el krib", "rouhia", "kesra", "bargou"],
    "Sousse": ["msaken", "hammam sousse", "kalaa kebira", "kalaa seghira", "akouda", "enfidha",
               "hergla", "sidi bou ali", "kondar", "sahloul", "khezama", "port el kantaoui",
               "zaouiet sousse", "bouficha"],
    "Monastir": ["ksar hellal", "moknine", "jemmal", "sahline", "teboulba", "bekalta",
                 "ksibet el mediouni", "bembla", "zeramdine", "ouerdanine", "beni hassen",
                 "sayada", "lamta", "khniss"],
    "Mahdia": ["ksour essef", "el jem", "chebba", "souassi", "boumerdes", "sidi alouane",
               "melloulech", "rejiche", "hbira", "chorbane"],
    "Sfax": ["sakiet ezzit", "sakiet eddaier", "thyna", "agareb", "jebeniana", "mahres",
             "el hencha", "kerkennah", "bir ali ben khelifa", "skhira", "menzel chaker",
             "ghraiba", "gremda"],
    "Kairouan": ["haffouz", "sbikha", "oueslatia", "bouhajla", "nasrallah", "hajeb el ayoun",
                 "cherarda"],
    "Kasserine": ["sbeitla", "feriana", "thala", "foussana", "sbiba", "jedliane",
                  "majel bel abbes", "hidra"],
    "Sidi Bouzid": ["regueb", "meknassy", "menzel bouzaiane", "jilma", "bir el hafey", "mezzouna",
                    "sidi ali ben aoun", "souk jedid", "ouled haffouz", "cebbala"],
    "Gabes": ["mareth", "matmata", "ghannouch", "metouia", "menzel el habib"],
    "Medenine": ["djerba", "jerba", "houmt souk", "midoun", "ajim", "zarzis", "ben gardane",
                 "ben guerdane", "beni khedache", "sidi makhlouf"],
    "Tataouine": ["ghomrassen", "remada", "dhehiba", "bir lahmar", "smar"],
    "Gafsa": ["metlaoui", "redeyef", "moulares", "om larayes", "mdhilla", "el guettar", "sened",
              "belkhir"],
    "Tozeur": ["nefta", "degache", "tameghza", "hazoua"],
    "Kebili": ["douz", "souk lahad", "faouar", "el golaa"],
}

_NOISE = re.compile(r"\b(gouvernorat|gouvernerat|governorate|gov|wilaya|wilayet|ville|centre)\b")


def clean(text: object) -> str:
    """Lowercase, strip accents, keep letters only, collapse doubled letters."""
    if not isinstance(text, str):
        return ""
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z]+", " ", t)
    t = _NOISE.sub(" ", t)
    t = re.sub(r"(.)\1+", r"\1", t)  # mannouba -> manouba, sfaxx -> sfax
    return re.sub(r"\s+", " ", t).strip()


def _build() -> tuple[dict[str, str], dict[str, str]]:
    names, cities = {}, {}
    for gov, aliases in GOVERNORATES.items():
        for a in [gov, *aliases]:
            names[clean(a)] = gov
    for gov, cs in CITIES.items():
        for c in cs:
            cities[clean(c)] = gov
    return names, cities


NAME_KEYS, CITY_KEYS = _build()
ALL_KEYS = {**CITY_KEYS, **NAME_KEYS}  # governorate names win on clashes
# Whole-word patterns, longest first so "sidi bou said" beats "said"
_PATTERNS = [(re.compile(rf"\b{re.escape(k)}\b"), g)
             for k, g in sorted(ALL_KEYS.items(), key=lambda kv: -len(kv[0])) if len(k) >= 4]


def find_in_text(text: object) -> str | None:
    """Return the governorate if exactly one governorate is named in the text."""
    t = clean(text)
    if not t:
        return None
    found = {g for p, g in _PATTERNS if p.search(t)}
    return found.pop() if len(found) == 1 else None


def resolve_label(label: object) -> tuple[str, str]:
    """Map one raw governorate label -> (governorate, method)."""
    k = clean(label)
    if not k:
        return UNKNOWN, "unknown"
    if k in NAME_KEYS:
        return NAME_KEYS[k], "exact"
    if k in CITY_KEYS:
        return CITY_KEYS[k], "city"
    if len(k) >= 4:
        m = difflib.get_close_matches(k, ALL_KEYS.keys(), n=1, cutoff=0.85)
        if m:
            return ALL_KEYS[m[0]], "fuzzy"
    g = find_in_text(k)
    if g:
        return g, "contains"
    return UNKNOWN, "unknown"
