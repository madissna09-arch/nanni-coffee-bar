"""Baut die Speisekarte aus menu.json.

- schreibt die Akkordeon-Karte in index.html (zwischen <!-- MENU:START --> und <!-- MENU:END -->)
- erzeugt karte.html, die eigenstaendige Kartenseite fuer QR-Code/NFC am Tisch

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
ICON = {"signature-drinks": "i-iced", "soft": "i-bottle", "bagel": "i-bagel", "waffeln": "i-waffle"}
TAG = {"vegan": ("tag-vegan", "vegan"), "veggie": ("tag-veggie", "veggie")}

e = lambda s: html.escape(s, quote=True)


def price_num(p):
    return float(p.replace(",", "."))


def thumb(c, size):
    if c.get("img"):
        return f'<span class="cat-thumb"><img src="{c["img"]}" alt="" loading="lazy" width="{size}" height="{size}"></span>'
    return f'<span class="cat-thumb cat-icon"><svg aria-hidden="true"><use href="#{ICON.get(c["id"], "i-cup")}"/></svg></span>'


def item_html(it):
    marks = ""
    for t in it.get("tags", []):
        cls, label = TAG[t]
        marks += f' <span class="tag {cls}"><svg aria-hidden="true"><use href="#i-leaf"/></svg>{label}</span>'
    if it.get("badge"):
        marks += f' <span class="tag tag-badge">{e(it["badge"])}</span>'
    desc = f'<p>{e(it["desc"])}</p>' if it.get("desc") else ""
    return (f'<li class="mi"><div class="mi-top"><h4>{e(it["name"])}{marks}</h4>'
            f'<span class="mi-line" aria-hidden="true"></span><span class="mi-price">{it["price"]}&nbsp;€</span></div>{desc}</li>')


def body_html(c):
    out = ""
    if c.get("callout"):
        out += (f'<div class="callout"><b>{e(c["callout"]["title"])}</b><p>{e(c["callout"]["text"])}</p></div>')
    out += '<ul class="mi-list">' + "".join(item_html(it) for it in c["items"]) + "</ul>"
    if c.get("note"):
        out += f'<p class="cat-note">{e(c["note"])}</p>'
    return out


# ---------- 1) Akkordeon fuer index.html ----------
acc = []
for i, c in enumerate(cats):
    low = min(price_num(it["price"]) for it in c["items"])
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
open(idx_path, "w", encoding="utf-8").write(idx)

# ---------- 2) karte.html ----------
chips = "".join(f'<a href="#{c["id"]}">{e(c["name"])}</a>' for c in cats)
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
                for it in c["items"]
            ],
        }
        for c in cats
    ],
}

tpl = open(os.path.join(HERE, "karte.template.html"), encoding="utf-8").read()
page = (tpl.replace("{{CHIPS}}", chips)
           .replace("{{SECTIONS}}", sections)
           .replace("{{STAND}}", e(menu["stand"]))
           .replace("{{JSONLD}}", json.dumps(ld, ensure_ascii=False, indent=1)))
open(os.path.join(HERE, "karte.html"), "w", encoding="utf-8").write(page)

print(f"{len(cats)} Kategorien, {sum(len(c['items']) for c in cats)} Positionen -> index.html + karte.html")
