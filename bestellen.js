// Bestellen am Tisch.
// Die Karte bleibt eine Lesekarte, solange sie ohne gültigen Tisch-Code (?t=...) geöffnet wird.
// Mit Code: Plus-Knöpfe an den Positionen, Warenkorb, Abschicken an die Theke, Stand der Bestellung.
// Zwei Arten von Code: Tisch-Code (NFC, der Tisch steht fest) und Laden-Code (der eine QR-Code auf allen
// Stickern, der Gast wählt seinen Tisch vor dem Abschicken selbst).
// Positionen und Extras kommen aus den data-n/data-p-Attributen, die build_menu.py in die Karte schreibt.
(() => {
  const code = new URLSearchParams(location.search).get('t');
  if (!code || !window.NANNI) return;
  NANNI.rpc('tisch_info', { p_code: code }).then(info => { if (info && info.ok) start(info); }).catch(() => {});

  const euro = c => (c / 100).toFixed(2).replace('.', ',') + ' €';
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v;
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), v); else if (v !== false && v != null) n.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) n.append(kid);
    return n;
  };
  const icon = d => { const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); s.setAttribute('viewBox', '0 0 16 16'); s.setAttribute('aria-hidden', 'true'); s.innerHTML = `<path d="${d}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>`; return s; };
  const PLUS = 'M8 2.5v11M2.5 8h11', MINUS = 'M2.5 8h11', CROSS = 'M3 3l10 10M13 3L3 13';
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* privater Modus */ } }
  };

  function start(info) {
    const css = el('link', { rel: 'stylesheet', href: 'bestellen.css' });
    css.addEventListener('load', sizeDock);
    document.head.append(css);
    document.body.classList.add('bst');

    const CART = 'nanni-korb-' + code, ORDERS = 'nanni-best-' + code, TISCH = 'nanni-tisch-' + code;
    const wahl = !!info.wahl;
    const label = t => 'Tisch ' + t.name + (t.bereich ? ' · ' + t.bereich : '');
    // Beim Laden-Code merkt sich das Handy den gewählten Tisch für drei Stunden
    let tisch = { name: info.tisch, bereich: info.bereich };
    if (wahl) {
      const saved = store.get(TISCH, null);
      tisch = saved && Date.now() - saved.ts < 3 * 3600e3 ? info.tische.find(t => t.id === saved.id) || null : null;
    }
    const pill = el(wahl ? 'button' : 'span', { class: 'bst-tisch', type: wahl ? 'button' : null, onclick: () => { if (wahl && info.aktiv) openPick(); } });
    const drawPill = () => pill.replaceChildren(el('b', { text: tisch ? label(tisch) : 'Tisch wählen' }),
      info.aktiv ? el('span', { text: wahl && tisch ? 'ändern' : 'Bestellt direkt hier am Handy' }) : '');
    drawPill();
    document.getElementById('status').after(el('br'), pill);
    let cart = store.get(CART, []);
    // Bestellungen bleiben 12 Stunden auf dem Handy sichtbar
    let orders = store.get(ORDERS, []).filter(o => Date.now() - o.ts < 12 * 3600e3);

    const dock = el('div', { class: 'bst-dock' });
    document.body.append(dock);

    if (!info.aktiv) {
      document.querySelector('.k-hero').append(el('div', { class: 'bst-pause' }, el('b', { text: 'Bestellen am Handy ist gerade pausiert.' }), 'Bestellt bitte direkt bei uns an der Theke.'));
    } else {
      document.querySelectorAll('.kcat').forEach(sec => {
        const extras = [...sec.querySelectorAll('.extras li[data-n]')].map(li => ({ name: li.dataset.n, cent: +li.dataset.p }));
        sec.querySelectorAll('.mi[data-n]').forEach(li => {
          const item = { name: li.dataset.n, cent: +li.dataset.p, desc: li.querySelector('p')?.textContent || '', extras };
          const btn = el('button', { class: 'mi-add', type: 'button', 'aria-label': item.name + ' hinzufügen', onclick: () => openItem(item) }, icon(PLUS));
          li.querySelector('.mi-top').append(btn);
          li._add = btn;
        });
      });
    }

    // ---------- Blatt: Position hinzufügen
    function sheet(title, sub) {
      const d = el('dialog', { class: 'bst-sheet' });
      const body = el('div', { class: 'bst-body' }), foot = el('div', { class: 'bst-foot' });
      d.append(el('div', { class: 'bst-head' }, el('div', { style: 'flex:1' }, el('h3', { text: title }), sub ? el('p', { text: sub }) : null),
        el('button', { class: 'bst-x', type: 'button', 'aria-label': 'Schließen', onclick: () => d.close() }, icon(CROSS))), body, foot);
      d.addEventListener('click', ev => { if (ev.target === d) d.close(); });
      d.addEventListener('close', () => d.remove());
      document.body.append(d);
      return { d, body, foot };
    }
    function qty(value, onchange, min = 1) {
      const out = el('output', { text: value });
      const step = n => { value = Math.max(min, Math.min(20, value + n)); out.textContent = value; onchange(value); };
      return el('div', { class: 'bst-qty' },
        el('button', { type: 'button', 'aria-label': 'Weniger', onclick: () => step(-1) }, icon(MINUS)), out,
        el('button', { type: 'button', 'aria-label': 'Mehr', onclick: () => step(1) }, icon(PLUS)));
    }

    // ---------- Blatt: Tisch wählen (nur beim gemeinsamen QR-Code)
    function openPick(then) {
      const s = sheet('An welchem Tisch sitzt ihr?', 'Die Nummer steht bei euch am Tisch.');
      const bereiche = [...new Set(info.tische.map(t => t.bereich))];
      for (const b of bereiche) {
        if (b) s.body.append(el('span', { class: 'bst-label', text: b }));
        s.body.append(el('div', { class: 'bst-grid' }, info.tische.filter(t => t.bereich === b).map(t =>
          el('button', { type: 'button', class: tisch && tisch.id === t.id ? 'on' : '', text: t.name, 'aria-label': label(t), onclick: () => {
            tisch = t; store.set(TISCH, { id: t.id, ts: Date.now() }); drawPill(); s.d.close(); if (then) then();
          } }))));
      }
      s.d.showModal();
    }

    function openItem(item) {
      const s = sheet(item.name, item.desc);
      let menge = 1;
      const boxes = item.extras.map(x => ({ x, input: el('input', { type: 'checkbox' }) }));
      if (boxes.length) {
        s.body.append(el('span', { class: 'bst-label', text: 'Extras' }),
          el('ul', { class: 'bst-opts' }, boxes.map(b => el('li', {}, el('label', {}, b.input, el('span', { text: b.x.name }), el('em', { text: '+' + euro(b.x.cent) }))))));
      }
      const note = el('textarea', { class: 'bst-note', rows: 2, maxlength: 200, placeholder: 'z. B. mit Hafermilch, koffeinfrei, ohne Zwiebeln' });
      s.body.append(el('span', { class: 'bst-label', text: 'Wunsch dazu' }), note);
      const add = el('button', { class: 'bst-btn', type: 'button' });
      const calc = () => {
        const one = item.cent + boxes.filter(b => b.input.checked).reduce((a, b) => a + b.x.cent, 0);
        add.replaceChildren(el('span', { text: 'Hinzufügen' }), el('span', { text: euro(one * menge) }));
      };
      boxes.forEach(b => b.input.addEventListener('change', calc));
      add.addEventListener('click', () => {
        const line = { name: item.name, cent: item.cent, menge, notiz: note.value.trim(),
          extras: boxes.filter(b => b.input.checked).map(b => ({ name: b.x.name, cent: b.x.cent })) };
        line.key = JSON.stringify([line.name, line.extras.map(x => x.name), line.notiz]);
        const same = cart.find(l => l.key === line.key);
        if (same) same.menge = Math.min(20, same.menge + menge); else cart.push(line);
        save(); s.d.close();
      });
      s.foot.append(el('div', { class: 'bst-row' }, qty(1, v => { menge = v; calc(); }), add));
      calc();
      s.d.showModal();
    }

    // ---------- Warenkorb
    const lineCent = l => (l.cent + l.extras.reduce((a, x) => a + x.cent, 0)) * l.menge;
    const total = () => cart.reduce((a, l) => a + lineCent(l), 0);
    const count = () => cart.reduce((a, l) => a + l.menge, 0);
    const detail = l => [...l.extras.map(x => x.name), l.notiz].filter(Boolean).join(' · ');
    function save() { store.set(CART, cart); renderDock(); }

    function openCart() {
      const s = sheet('Eure Bestellung', wahl ? '' : label(tisch));
      const list = el('ul', { class: 'bst-lines' });
      const row = el('button', { class: 'bst-tischrow', type: 'button', onclick: () => openPick(drawRow) });
      const drawRow = () => row.replaceChildren(el('b', { text: tisch ? label(tisch) : 'Euer Tisch' }), el('span', { text: tisch ? 'ändern' : 'bitte wählen' }));
      drawRow();
      const sum = el('span'), err = el('p', { class: 'bst-err', hidden: true, role: 'alert' });
      const send = el('button', { class: 'bst-btn center', type: 'button', text: 'Bestellung abschicken' });
      const draw = () => {
        if (!cart.length) return s.d.close();
        list.replaceChildren(...cart.map(l => el('li', {},
          qty(l.menge, v => { if (v === 0) cart = cart.filter(x => x !== l); else l.menge = v; save(); draw(); }, 0),
          el('div', { class: 't' }, el('b', { text: l.name }), detail(l) ? el('small', { text: detail(l) }) : null),
          el('span', { class: 'p', text: euro(lineCent(l)) }))));
        sum.textContent = euro(total());
      };
      s.body.append(list);
      s.foot.append(wahl ? row : null, el('div', { class: 'bst-sum' }, el('span', { text: 'Summe' }), sum), err,
        el('p', { class: 'bst-fine', text: 'Bezahlt wird wie gewohnt bei uns im Café.' }), send);
      send.addEventListener('click', async () => {
        if (!tisch) return openPick(() => { drawRow(); send.click(); });
        send.disabled = true; send.textContent = 'Wird gesendet …'; err.hidden = true;
        const fail = msg => { err.textContent = msg; err.hidden = false; send.disabled = false; send.textContent = 'Bestellung abschicken'; };
        let res;
        try {
          res = await NANNI.rpc('bestellung_aufgeben', { ...(wahl ? { p_tisch: tisch.id } : {}), p_code: code, p_positionen: cart.map(l => ({
            name: l.name, menge: l.menge, preis_cent: l.cent, notiz: l.notiz, extras: l.extras.map(x => ({ name: x.name, preis_cent: x.cent })) })) });
        } catch { return fail('Keine Verbindung. Prüft kurz euer Netz und versucht es noch einmal.'); }
        if (!res.ok) {
          return fail({ pausiert: 'Bestellen am Handy ist gerade pausiert. Bestellt bitte an der Theke.',
            zuviele: 'Von eurem Tisch warten schon Bestellungen bei uns. Einen Moment, wir sind gleich so weit.',
            tisch: 'Dieser Tisch-Link gilt nicht mehr. Scannt den Code am Tisch bitte noch einmal.' }[res.fehler]
            || 'Das hat nicht geklappt. Bestellt bitte an der Theke.');
        }
        orders.unshift({ id: res.id, nr: res.nr, ts: Date.now(), status: 'neu', summe: res.summe_cent, tisch: label(tisch),
          zeilen: cart.map(l => ({ menge: l.menge, name: l.name, detail: detail(l) })) });
        store.set(ORDERS, orders);
        cart = []; save(); s.d.close(); openOrders(); poll();
      });
      draw();
      s.d.showModal();
    }

    // ---------- Stand der Bestellungen
    const TXT = {
      neu: ['Ist bei uns angekommen', 'Wir schauen gleich drauf.'],
      angenommen: ['Wird gerade zubereitet', 'Wir bringen es euch an den Tisch.'],
      serviert: ['Serviert', 'Lasst es euch schmecken.'],
      abgelehnt: ['Konnten wir nicht annehmen', 'Kommt bitte kurz zu uns an die Theke.']
    };
    const zeit = ts => new Date(ts).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    const done = o => o.status === 'serviert' || o.status === 'abgelehnt';
    let ordersBody = null;
    function drawOrders() {
      if (!ordersBody) return;
      ordersBody.replaceChildren(...orders.map(o => el('article', { class: 'bst-order', 'data-s': o.status },
        el('header', {}, el('i'), el('b', { text: TXT[o.status][0] }), el('small', { text: zeit(o.ts) + ' Uhr' + (wahl && o.tisch ? ' · ' + o.tisch : '') })),
        el('p', { text: TXT[o.status][1] }),
        el('ul', {}, o.zeilen.map(z => el('li', {}, z.menge + ' × ' + z.name, z.detail ? el('small', { text: ' · ' + z.detail }) : null))))));
    }
    function openOrders() {
      const s = sheet('Eure Bestellungen', (wahl ? '' : label(tisch) + ' · ') + 'Bezahlt wird wie gewohnt bei uns im Café.');
      ordersBody = s.body; drawOrders();
      s.d.addEventListener('close', () => { ordersBody = null; });
      s.foot.append(el('button', { class: 'bst-btn alt center', type: 'button', text: 'Weiter in der Karte', onclick: () => s.d.close() }));
      s.d.showModal();
    }

    let timer = null;
    async function poll() {
      clearTimeout(timer);
      const open = orders.filter(o => !done(o));
      if (!open.length || document.hidden) return;
      try {
        const res = await NANNI.rpc('bestellung_status', { p_ids: open.map(o => o.id) });
        let changed = false;
        for (const r of res) {
          const o = orders.find(x => x.id === r.id);
          if (o && o.status !== r.status) { o.status = r.status; if (done(o)) o.doneAt = Date.now(); changed = true; }
        }
        if (changed) { store.set(ORDERS, orders); renderDock(); drawOrders(); }
      } catch { /* nächster Versuch */ }
      timer = setTimeout(poll, 5000);
    }
    document.addEventListener('visibilitychange', poll);

    // ---------- Leiste unten: Stand der letzten Bestellung + Warenkorb
    function renderDock() {
      dock.replaceChildren();
      const last = orders[0];
      // fertige Bestellungen verschwinden nach 15 Minuten aus der Leiste
      if (last && !(done(last) && Date.now() - (last.doneAt || last.ts) > 15 * 60e3)) {
        const more = orders.filter(o => !done(o)).length;
        dock.append(el('button', { class: 'bst-pill', type: 'button', 'data-s': last.status, onclick: openOrders },
          el('i'), el('span', { class: 'l' }, el('b', { text: 'Bestellung ' + zeit(last.ts) + ' Uhr' }), ' · ' + TXT[last.status][0]),
          el('span', { class: 'm', text: more > 1 ? more + ' offen' : 'ansehen' })));
      }
      if (cart.length) {
        dock.append(el('button', { class: 'bst-bar', type: 'button', onclick: openCart },
          el('span', { class: 'n', text: count() }), el('span', { class: 'l', text: 'Bestellung ansehen' }), el('span', { class: 's', text: euro(total()) })));
      }
      document.querySelectorAll('.mi[data-n]').forEach(li => {
        if (!li._add) return;
        const n = cart.filter(l => l.name === li.dataset.n).reduce((a, l) => a + l.menge, 0);
        li._add.classList.toggle('has', n > 0);
        if (n > 0) li._add.textContent = n; else li._add.replaceChildren(icon(PLUS));
      });
      sizeDock();
    }
    function sizeDock() {
      document.body.classList.toggle('bst-has-dock', dock.childElementCount > 0);
      document.body.style.setProperty('--bst-dock', dock.offsetHeight + 'px');
    }
    renderDock();
    poll();
    setInterval(renderDock, 60e3);
  }
})();
