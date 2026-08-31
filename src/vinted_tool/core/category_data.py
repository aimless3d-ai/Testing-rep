"""Curated Vinted category catalogue.

Vinted does not publish an open category API, so the catalogue is maintained
here as data. Each entry carries the German category path, matching keywords,
a realistic second-hand base price (EUR, "sehr gut" condition, no-name brand)
and the size system that applies.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CategoryEntry:
    path: tuple[str, ...]
    keywords: tuple[str, ...]
    base_price: float
    size_system: str  # "clothing" | "shoes" | "none" | "kids"

    @property
    def label(self) -> str:
        return " > ".join(self.path)


W = "Damen"
M = "Herren"
K = "Kinder"

CATEGORIES: tuple[CategoryEntry, ...] = (
    # -------------------------------------------------------------- Damen
    CategoryEntry((W, "Kleidung", "Oberteile & T-Shirts", "T-Shirts"),
                  ("t-shirt", "tshirt", "shirt", "tee"), 8.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Oberteile & T-Shirts", "Blusen"),
                  ("bluse", "blouse", "tunika"), 12.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Oberteile & T-Shirts", "Tops"),
                  ("top", "trägertop", "camisole", "spaghettiträger"), 7.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Pullover & Sweatshirts", "Pullover"),
                  ("pullover", "pulli", "sweater", "strickpullover", "strick"), 15.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Pullover & Sweatshirts", "Hoodies"),
                  ("hoodie", "kapuzenpullover", "kapuzenpulli"), 18.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Pullover & Sweatshirts", "Sweatshirts"),
                  ("sweatshirt", "sweater", "crewneck"), 14.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Kleider", "Freizeitkleider"),
                  ("kleid", "dress", "sommerkleid", "freizeitkleid"), 16.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Kleider", "Abendkleider"),
                  ("abendkleid", "cocktailkleid", "ballkleid", "maxikleid"), 28.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Hosen & Leggings", "Jeans"),
                  ("jeans", "denim", "skinny", "mom jeans", "boyfriend"), 18.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Hosen & Leggings", "Stoffhosen"),
                  ("stoffhose", "chino", "anzughose", "hose"), 14.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Hosen & Leggings", "Leggings"),
                  ("leggings", "jeggings", "treggings"), 9.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Röcke", "Miniröcke"),
                  ("minirock", "rock kurz"), 11.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Röcke", "Midiröcke"),
                  ("rock", "midirock", "faltenrock", "skirt"), 13.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Jacken & Mäntel", "Jacken"),
                  ("jacke", "übergangsjacke", "jacket", "bomberjacke"), 25.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Jacken & Mäntel", "Winterjacken"),
                  ("winterjacke", "daunenjacke", "steppjacke", "parka"), 38.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Jacken & Mäntel", "Mäntel"),
                  ("mantel", "wollmantel", "trenchcoat", "coat"), 35.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Jacken & Mäntel", "Jeansjacken"),
                  ("jeansjacke", "denim jacket"), 22.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Sportbekleidung", "Sport-Oberteile"),
                  ("sport top", "sport-bh", "sportshirt", "funktionsshirt"), 10.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Sportbekleidung", "Sporthosen"),
                  ("sporthose", "jogginghose", "trainingshose", "sweatpants"), 14.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Blazer & Anzüge", "Blazer"),
                  ("blazer", "sakko damen"), 24.0, "clothing"),
    CategoryEntry((W, "Kleidung", "Bademode", "Bikinis"),
                  ("bikini", "badeanzug", "swimsuit"), 12.0, "clothing"),
    CategoryEntry((W, "Schuhe", "Sneaker"),
                  ("sneaker", "turnschuh", "trainers", "laufschuh"), 30.0, "shoes"),
    CategoryEntry((W, "Schuhe", "Stiefel"),
                  ("stiefel", "boots", "stiefelette", "chelsea"), 30.0, "shoes"),
    CategoryEntry((W, "Schuhe", "Sandalen"),
                  ("sandale", "sandalette", "flip flop", "zehentrenner"), 15.0, "shoes"),
    CategoryEntry((W, "Schuhe", "Absatzschuhe"),
                  ("pumps", "high heels", "absatzschuh", "heels"), 22.0, "shoes"),
    CategoryEntry((W, "Schuhe", "Halbschuhe & Ballerinas"),
                  ("ballerina", "loafer", "halbschuh", "slipper"), 18.0, "shoes"),
    CategoryEntry((W, "Accessoires", "Taschen", "Handtaschen"),
                  ("handtasche", "tasche", "shopper", "umhängetasche", "bag"), 25.0, "none"),
    CategoryEntry((W, "Accessoires", "Taschen", "Rucksäcke"),
                  ("rucksack", "backpack", "daypack"), 25.0, "none"),
    CategoryEntry((W, "Accessoires", "Schmuck", "Halsketten"),
                  ("kette", "halskette", "collier", "necklace"), 12.0, "none"),
    CategoryEntry((W, "Accessoires", "Schmuck", "Ohrringe"),
                  ("ohrring", "creole", "stecker", "earrings"), 10.0, "none"),
    CategoryEntry((W, "Accessoires", "Uhren"),
                  ("uhr", "armbanduhr", "watch"), 35.0, "none"),
    CategoryEntry((W, "Accessoires", "Gürtel"),
                  ("gürtel", "belt"), 12.0, "none"),
    CategoryEntry((W, "Accessoires", "Schals & Tücher"),
                  ("schal", "tuch", "loop", "scarf"), 10.0, "none"),
    CategoryEntry((W, "Accessoires", "Mützen & Hüte"),
                  ("mütze", "beanie", "hut", "cap", "kappe"), 10.0, "none"),
    CategoryEntry((W, "Accessoires", "Sonnenbrillen"),
                  ("sonnenbrille", "brille", "sunglasses"), 15.0, "none"),
    # -------------------------------------------------------------- Herren
    CategoryEntry((M, "Kleidung", "T-Shirts"),
                  ("herren t-shirt", "männer shirt"), 9.0, "clothing"),
    CategoryEntry((M, "Kleidung", "Hemden"),
                  ("hemd", "shirt langarm", "businesshemd"), 14.0, "clothing"),
    CategoryEntry((M, "Kleidung", "Pullover & Sweatshirts"),
                  ("herren pullover", "herren hoodie", "herren sweatshirt"), 18.0, "clothing"),
    CategoryEntry((M, "Kleidung", "Jeans"),
                  ("herren jeans", "männer jeans"), 20.0, "clothing"),
    CategoryEntry((M, "Kleidung", "Hosen"),
                  ("herren hose", "chino herren", "cargohose"), 16.0, "clothing"),
    CategoryEntry((M, "Kleidung", "Jacken & Mäntel"),
                  ("herren jacke", "herren mantel", "herren parka"), 30.0, "clothing"),
    CategoryEntry((M, "Kleidung", "Anzüge & Sakkos"),
                  ("anzug", "sakko", "anzugjacke"), 40.0, "clothing"),
    CategoryEntry((M, "Kleidung", "Sportbekleidung"),
                  ("herren sporthose", "herren trikot", "trikot"), 16.0, "clothing"),
    CategoryEntry((M, "Schuhe", "Sneaker"),
                  ("herren sneaker", "herren turnschuh"), 35.0, "shoes"),
    CategoryEntry((M, "Schuhe", "Stiefel & Boots"),
                  ("herren boots", "herren stiefel"), 35.0, "shoes"),
    CategoryEntry((M, "Schuhe", "Business-Schuhe"),
                  ("business schuh", "lederschuh", "budapester", "oxford"), 30.0, "shoes"),
    CategoryEntry((M, "Accessoires", "Taschen & Rucksäcke"),
                  ("herren tasche", "herren rucksack", "aktentasche"), 25.0, "none"),
    CategoryEntry((M, "Accessoires", "Uhren"),
                  ("herrenuhr", "chronograph"), 45.0, "none"),
    CategoryEntry((M, "Accessoires", "Gürtel"),
                  ("herrengürtel", "ledergürtel"), 14.0, "none"),
    # -------------------------------------------------------------- Kinder
    CategoryEntry((K, "Kleidung", "Oberteile"),
                  ("kinder shirt", "baby body", "strampler", "kinder pullover"), 5.0, "kids"),
    CategoryEntry((K, "Kleidung", "Hosen"),
                  ("kinderhose", "baby hose", "kinder jeans"), 6.0, "kids"),
    CategoryEntry((K, "Kleidung", "Jacken"),
                  ("kinderjacke", "matschjacke", "schneeanzug"), 14.0, "kids"),
    CategoryEntry((K, "Schuhe"),
                  ("kinderschuh", "babyschuh", "lauflernschuh"), 12.0, "shoes"),
    CategoryEntry((K, "Spielzeug"),
                  ("spielzeug", "plüschtier", "puppe", "bausteine", "lego"), 10.0, "none"),
    # ---------------------------------------------------------------- Home
    CategoryEntry(("Zuhause", "Dekoration"),
                  ("deko", "vase", "kerzenhalter", "bilderrahmen"), 10.0, "none"),
    CategoryEntry(("Zuhause", "Küche"),
                  ("küche", "geschirr", "tasse", "teller", "pfanne"), 12.0, "none"),
    CategoryEntry(("Zuhause", "Textilien"),
                  ("kissen", "decke", "vorhang", "bettwäsche"), 12.0, "none"),
    # -------------------------------------------------------- Unterhaltung
    CategoryEntry(("Unterhaltung", "Bücher"),
                  ("buch", "roman", "sachbuch", "taschenbuch"), 5.0, "none"),
    CategoryEntry(("Unterhaltung", "Videospiele"),
                  ("videospiel", "playstation", "nintendo", "xbox", "spiel konsole"), 18.0, "none"),
    CategoryEntry(("Unterhaltung", "Filme & Musik"),
                  ("dvd", "blu-ray", "cd", "vinyl", "schallplatte"), 6.0, "none"),
    CategoryEntry(("Elektronik", "Kopfhörer"),
                  ("kopfhörer", "headset", "earbuds", "in-ear"), 25.0, "none"),
    CategoryEntry(("Elektronik", "Handys & Zubehör"),
                  ("handy", "smartphone", "handyhülle", "ladekabel"), 40.0, "none"),
    CategoryEntry(("Elektronik", "Konsolen & Zubehör"),
                  ("konsole", "controller", "gamepad"), 45.0, "none"),
    # -------------------------------------------------------------- Beauty
    CategoryEntry(("Beauty", "Parfum"),
                  ("parfum", "eau de toilette", "duft"), 20.0, "none"),
    CategoryEntry(("Beauty", "Make-up"),
                  ("make-up", "lippenstift", "lidschatten", "palette"), 10.0, "none"),
)

BRAND_PRICE_TIERS: dict[str, float] = {
    # premium / designer
    "gucci": 3.4, "prada": 3.4, "louis vuitton": 3.6, "burberry": 3.0, "moncler": 3.2,
    "canada goose": 3.0, "balenciaga": 3.2, "dior": 3.4, "chanel": 3.6, "hermes": 3.6,
    # higher mid range
    "boss": 2.0, "hugo boss": 2.0, "polo ralph lauren": 2.1, "ralph lauren": 2.1,
    "tommy hilfiger": 1.8, "lacoste": 1.8, "calvin klein": 1.7, "guess": 1.6,
    "the north face": 2.0, "patagonia": 2.1, "arc'teryx": 2.4, "jack wolfskin": 1.6,
    "stone island": 2.8, "cp company": 2.4, "carhartt": 1.8, "dr. martens": 1.9,
    "nike": 1.6, "adidas": 1.6, "new balance": 1.6, "puma": 1.4, "asics": 1.5,
    "levis": 1.5, "levi's": 1.5, "diesel": 1.6, "g-star": 1.5, "napapijri": 1.8,
    "champion": 1.4, "vans": 1.4, "converse": 1.4, "birkenstock": 1.7, "timberland": 1.7,
    "michael kors": 1.9, "coach": 1.9, "furla": 1.9, "swarovski": 1.8, "pandora": 1.7,
    "fossil": 1.5, "casio": 1.4, "seiko": 1.9, "apple": 2.2, "sony": 1.6, "bose": 1.9,
    "samsung": 1.6, "jbl": 1.4, "nintendo": 1.6, "lego": 1.7,
    # mid range
    "zara": 1.1, "mango": 1.1, "cos": 1.4, "arket": 1.3, "other stories": 1.3,
    "massimo dutti": 1.4, "marc o'polo": 1.4, "s.oliver": 1.0, "esprit": 1.0,
    "tom tailor": 1.0, "only": 0.9, "vero moda": 0.9, "jack & jones": 0.9,
    "urban outfitters": 1.2, "weekday": 1.1, "monki": 0.9, "bershka": 0.8,
    # value
    "h&m": 0.75, "primark": 0.6, "shein": 0.5, "c&a": 0.7, "kik": 0.5,
    "takko": 0.6, "new yorker": 0.7, "pull&bear": 0.8, "stradivarius": 0.8,
}

CLOTHING_SIZES = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL",
                  "32", "34", "36", "38", "40", "42", "44", "46", "48", "50", "52"]
SHOE_SIZES = [str(n) for n in range(16, 51)]
KIDS_SIZES = ["50", "56", "62", "68", "74", "80", "86", "92", "98", "104", "110",
              "116", "122", "128", "134", "140", "146", "152", "158", "164"]

COLORS = [
    "Schwarz", "Weiß", "Grau", "Beige", "Braun", "Blau", "Dunkelblau", "Hellblau",
    "Türkis", "Grün", "Dunkelgrün", "Gelb", "Orange", "Rot", "Bordeaux", "Rosa",
    "Pink", "Lila", "Gold", "Silber", "Mehrfarbig",
]

MATERIALS = [
    "Baumwolle", "Polyester", "Wolle", "Leder", "Kunstleder", "Leinen", "Seide",
    "Viskose", "Denim", "Jersey", "Fleece", "Daunen", "Kaschmir", "Nylon", "Elasthan",
]
