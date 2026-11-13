"""Baut die Speisekarte aus menu.json.

- schreibt die Akkordeon-Karte in index.html (zwischen <!-- MENU:START --> und <!-- MENU:END -->)
- erzeugt karte.html, die eigenstaendige Kartenseite fuer QR-Code/NFC am Tisch
- liest bestellsystem/allergene.json: solange dort "geprueft": false steht, erscheint davon nichts auf der Karte;
  es entsteht nur die Pruefliste bestellsystem/allergene-pruefliste.html fuer das Cafe

Aufruf: python build_menu.py   (nach jeder Aenderung an menu.json)
"""
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
menu = json.load(open(os.path.join(HERE, "menu.json"), encoding="utf-8"))
cats = menu["kategorien"]

# Kategorien ohne Foto bekommen ein Linien-Icon (Symbole stehen in beiden Seiten im <defs>-Block)
ICON = {"favourites": "i-iced", "fresh": "i-citrus", "soft": "i-bottle", "fruehstueck": "i-egg",
        "bowls": "i-bowl", "bagels": "i-bagel", "waffeln": "i-waffle"}
# Markierung -> (CSS-Klasse, Text, Icon)
TAG = {"vegan": ("tag-vegan", "vegan", "i-leaf"), "veggie": ("tag-veggie", "veggie", "i-leaf"),
       "vegan-opt": ("tag-vegan", "vegan möglich", "i-leaf"), "scharf": ("tag-hot", "scharf", "i-chili")}
ADDONS = menu.get("addons", [])

e = lambda s: html.escape(s, quote=True)

# Allergene und Zusatzstoffe (Entwurf, bis das Cafe ihn geprueft hat)
ALG_PATH = os.path.join(HERE, "bestellsystem", "allergene.json")  # liegt nicht im Git, solange es ein Entwurf ist
ALG = json.load(open(ALG_PATH, encoding="utf-8")) if os.path.exists(ALG_PATH) else {"geprueft": False, "positionen": {}, "extras": {}}
ALG_OK = ALG.get("geprueft") is True


def alg_text(entry):
    """Kennzeichnung fuer die Karte: nur bestaetigte Angaben ('ja' und 'zusatz')."""
    teile = [", ".join(entry.get("ja", [])), ", ".join(entry.get("zusatz", []))]
    return " · ".join(t for t in teile if t)


def price_num(p):
    return float(p.replace(",", "."))


def cents(p):
    """Preis in Cent; data-n/data-p an Positionen und Extras liest bestellen.js (Bestellen am Tisch)."""
    return round(price_num(p) * 100)


def thumb(c, size):
    if c.get("img"):
        return f'<span class="cat-thumb"><img src="{c["img"]}" alt="" loading="lazy" width="{size}" height="{size}"></span>'
    return f'<span class="cat-thumb cat-icon"><svg aria-hidden="true"><use href="#{ICON.get(c["id"], "i-cup")}"/></svg></span>'


def groups(c):
    """Kategorie als Liste von (Ueberschrift, Positionen); ohne Untergruppen eine Gruppe ohne Titel."""
    return [(g["title"], g["items"]) for g in c["groups"]] if c.get("groups") else [(None, c["items"])]


def all_items(c):
    return [it for _, items in groups(c) for it in items]


def item_html(it):
    marks = ""
    for t in it.get("tags", []):
        cls, label, icon = TAG[t]
        marks += f' <span class="tag {cls}"><svg aria-hidden="true"><use href="#{icon}"/></svg>{label}</span>'
    if it.get("badge"):
        marks += f' <span class="tag tag-badge">{e(it["badge"])}</span>'
    desc = f'<p>{e(it["desc"])}</p>' if it.get("desc") else ""
    kennz = alg_text(ALG["positionen"].get(it["name"], {})) if ALG_OK else ""
    if kennz:
        desc += f'<p class="mi-alg" style="font-size:.8em;opacity:.7;margin-top:2px">Enthält: {e(kennz)}</p>'
    return (f'<li class="mi" data-n="{e(it["name"])}" data-p="{cents(it["price"])}"><div class="mi-top"><h4>{e(it["name"])}{marks}</h4>'
            f'<span class="mi-line" aria-hidden="true"></span><span class="mi-price">{it["price"]}&nbsp;€</span></div>{desc}</li>')


def body_html(c):
    out = ""
    if c.get("callout"):
        out += (f'<div class="callout"><b>{e(c["callout"]["title"])}</b><p>{e(c["callout"]["text"])}</p></div>')
    for title, items in groups(c):
        if title:
            out += f'<h5 class="mi-group">{e(title)}</h5>'
        out += '<ul class="mi-list">' + "".join(item_html(it) for it in items) + "</ul>"
    blocks = list(c.get("extras", []))
    if c.get("addons"):
        blocks.append({"title": "Add-ons", "items": ADDONS})
    for b in blocks:
        out += (f'<div class="extras"><b>{e(b["title"])}</b><ul>'
                + "".join(f'<li data-n="{e(n)}" data-p="{cents(p)}">{e(n)} <span>+{p}&nbsp;€</span></li>' for n, p in b["items"]) + "</ul></div>")
    if c.get("notes"):
        out += '<ul class="cat-notes">' + "".join(f"<li>{e(n)}</li>" for n in c["notes"]) + "</ul>"
    return out


# ---------- 1) Akkordeon fuer index.html ----------
acc = []
for i, c in enumerate(cats):
    low = min(price_num(it["price"]) for it in all_items(c))
    low_s = f"{low:.2f}".replace(".", ",")
    acc.append(
        f'<details class="cat" name="karte" id="k-{c["id"]}"{" open" if i == 0 else ""}>'
        f'<summary>{thumb(c, 56)}<span class="cat-title"><b>{e(c["name"])}</b><small>{e(c["sub"])}</small></span>'
        f'<span class="cat-meta">ab {low_s}&nbsp;€</span><span class="cat-plus" aria-hidden="true"></span></summary>'
        f'<div class="cat-body">{body_html(c)}</div></details>'
    )
fragment = "\n".join(acc)

idx_path = os.path.join(HERE, "index.html")
idx = open(idx_path, encoding="utf-8").read()
idx, n = re.subn(r"(<!-- MENU:START -->).*?(<!-- MENU:END -->)", lambda m: m.group(1) + "\n" + fragment + "\n" + m.group(2), idx, flags=re.S)
assert n == 1, "Marker in index.html nicht gefunden"

if ALG_OK:
    legende = "; ".join(f"{k} = {v}" for k, v in ALG["allergene"].items()) + ". Zusatzstoffe: " + "; ".join(f"{k} = {v}" for k, v in ALG["zusatzstoffe"].items())
    alg_zeile = "Allergene und Zusatzstoffe stehen bei jeder Position. " + e(legende) + ". Spuren anderer Allergene sind möglich, fragt uns gern."
else:
    alg_zeile = "Allergene und Zusatzstoffe nennen wir dir gern im Café, sprich uns einfach an."
idx, n = re.subn(r"(<!-- ALG:START -->).*?(<!-- ALG:END -->)", lambda m: m.group(1) + alg_zeile + m.group(2), idx, flags=re.S)
assert n == 1, "ALG-Marker in index.html nicht gefunden"
open(idx_path, "w", encoding="utf-8").write(idx)

# ---------- 2) karte.html ----------
chips = "".join(f'<a href="#{c["id"]}">{e(c.get("short", c["name"]))}</a>' for c in cats)
sections = "".join(
    f'<section class="kcat" id="{c["id"]}"><header class="kcat-head">{thumb(c, 64)}'
    f'<div><h2>{e(c["name"])}</h2><p>{e(c["sub"])}</p></div></header>{body_html(c)}</section>'
    for c in cats
)

ld = {
    "@context": "https://schema.org",
    "@type": "Menu",
    "name": "Speisekarte NANNI Coffee & Bar",
    "inLanguage": "de",
    "hasMenuSection": [
        {
            "@type": "MenuSection",
            "name": c["name"],
            "hasMenuItem": [
                {k: v for k, v in {
                    "@type": "MenuItem",
                    "name": it["name"],
                    "description": it.get("desc"),
                    "suitableForDiet": {"vegan": "https://schema.org/VeganDiet", "veggie": "https://schema.org/VegetarianDiet"}.get((it.get("tags") or [None])[0]),
                    "offers": {"@type": "Offer", "price": f'{price_num(it["price"]):.2f}', "priceCurrency": "EUR"},
                }.items() if v}
                for it in all_items(c)
            ],
        }
        for c in cats
    ],
}

tpl = open(os.path.join(HERE, "karte.template.html"), encoding="utf-8").read()
page = (tpl.replace("{{CHIPS}}", chips)
           .replace("{{SECTIONS}}", sections)
           .replace("{{STAND}}", e(menu["stand"]))
           .replace("{{ALLERGENE}}", alg_zeile)
           .replace("{{JSONLD}}", json.dumps(ld, ensure_ascii=False, indent=1)))
open(os.path.join(HERE, "karte.html"), "w", encoding="utf-8").write(page)

print(f"{len(cats)} Kategorien, {sum(len(all_items(c)) for c in cats)} Positionen -> index.html + karte.html")

# ---------- 2b) karte.json: Positionsnamen je Kategorie fuer den Ausverkauft-Schalter auf theke.html ----------
# Die Namen muessen genau den data-n-Attributen der Karte entsprechen (die schickt die Gastseite beim Bestellen).
karte_json = {"stand": menu["stand"],
              "kategorien": [{"id": c["id"], "name": c["name"], "positionen": [it["name"] for it in all_items(c)]} for c in cats]}
with open(os.path.join(HERE, "karte.json"), "w", encoding="utf-8") as f:
    json.dump(karte_json, f, ensure_ascii=False, indent=1)
    f.write("\n")


# ---------- 3) Pruefliste Allergene fuer das Cafe ----------
alle = [it["name"] for c in cats for it in all_items(c)]
extra_namen = list(dict.fromkeys(n for c in cats for b in c.get("extras", []) for n, _ in b["items"])) + [n for n, _ in ADDONS]
extra_namen = list(dict.fromkeys(extra_namen))
fehlt = [n for n in alle if n not in ALG["positionen"]] + [n for n in extra_namen if n not in ALG["extras"]]
zuviel = [n for n in ALG["positionen"] if n not in alle] + [n for n in ALG["extras"] if n not in extra_namen]
assert not fehlt and not zuviel, f"allergene.json passt nicht zur Karte. Fehlt: {fehlt} / unbekannt: {zuviel}"


def zeile(name, en):
    ja = ", ".join(en.get("ja", [])) or "–"
    pr = ", ".join(en.get("pruefen", []))
    zu = ", ".join(en.get("zusatz", []))
    return (f'<tr><td class="n">{e(name)}</td><td class="c">{e(ja)}</td><td class="c">{e(pr)}</td><td class="c">{e(zu)}</td>'
            f'<td class="f">{e(en.get("frage", ""))}</td><td class="k"></td><td class="b"></td></tr>')


kopf = '<tr><th>Position</th><th>Enthält sicher</th><th>Bitte prüfen</th><th>Zusatz&shy;stoffe?</th><th>Frage an euch</th><th>Richtig so</th><th>Korrektur</th></tr>'
teile = []
for c in cats:
    teile.append(f'<h2>{e(c["name"])}</h2><table>{kopf}' + "".join(zeile(it["name"], ALG["positionen"][it["name"]]) for it in all_items(c)) + "</table>")
teile.append(f'<h2>Extras und Add-ons</h2><table>{kopf}' + "".join(zeile(n, ALG["extras"][n]) for n in extra_namen) + "</table>")
leg_a = "".join(f"<li><b>{k}</b> {e(v)}</li>" for k, v in ALG.get("allergene", {}).items())
leg_z = "".join(f"<li><b>{k}</b> {e(v)}</li>" for k, v in ALG.get("zusatzstoffe", {}).items())
allg = "".join(f"<li>{e(t)}</li>" for t in ALG.get("allgemein", []))
liste = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>NANNI · Prüfliste Allergene und Zusatzstoffe</title>
<style>
body {{ font: 14px/1.4 "Segoe UI", system-ui, sans-serif; color: #2b211b; margin: 24px auto; max-width: 1050px; padding: 0 16px; }}
h1 {{ font-size: 1.5rem; margin: 0 0 6px; }} h2 {{ font-size: 1.05rem; margin: 26px 0 6px; }}
.warn {{ background: #fff3c4; border: 1px solid #c9a400; border-radius: 8px; padding: 10px 14px; }}
table {{ width: 100%; border-collapse: collapse; }} th, td {{ border: 1px solid #c9bfae; padding: 5px 7px; text-align: left; vertical-align: top; }}
th {{ background: #f1e9dc; font-size: .8rem; }} td.n {{ width: 22%; font-weight: 600; }} td.c {{ width: 8%; }} td.k {{ width: 7%; }} td.b {{ width: 15%; }}
td.f {{ font-size: .86rem; color: #4d4038; }}
ul.leg {{ columns: 2; padding-left: 18px; margin: 6px 0; }} li {{ margin: 2px 0; }}
@media print {{ body {{ margin: 0; max-width: none; font-size: 11px; }} h2 {{ break-after: avoid; }} tr {{ break-inside: avoid; }} }}
</style></head><body>
<h1>NANNI Coffee &amp; Bar · Prüfliste Allergene und Zusatzstoffe</h1>
<p class="warn"><b>Entwurf, noch nicht geprüft.</b> Diese Liste hat eine KI aus den Beschreibungen der Karte abgeleitet (Stand der Karte: {e(menu["stand"])}).
Sie ersetzt keine Zutatenlisten. Bitte jede Zeile gegen eure Rezepte und die Etiketten eurer Lieferanten prüfen: Häkchen bei „Richtig so“ oder die Korrektur daneben schreiben.
Erst danach kommt die Kennzeichnung auf die Karte.</p>
<p><b>Enthält sicher</b> ergibt sich aus der Beschreibung. <b>Bitte prüfen</b> hängt vom gekauften Produkt oder vom Rezept ab. Leere Felder heißen: nichts erkannt, bitte trotzdem kurz bestätigen.</p>
<h2>Allergene</h2><ul class="leg">{leg_a}</ul>
<h2>Zusatzstoffe</h2><ul class="leg">{leg_z}</ul>
<h2>Allgemeine Fragen</h2><ul>{allg}</ul>
{"".join(teile)}
</body></html>
"""
os.makedirs(os.path.join(HERE, "bestellsystem"), exist_ok=True)
open(os.path.join(HERE, "bestellsystem", "allergene-pruefliste.html"), "w", encoding="utf-8").write(liste)
print(f"Allergene: {'auf der Karte' if ALG_OK else 'noch nicht geprüft, nur Prüfliste'} ({len(alle)} Positionen, {len(extra_namen)} Extras)")
