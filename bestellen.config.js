// Verbindung zur Bestell-Datenbank (Supabase-Projekt "nanni-bestellung").
// Lokal testen: url und key leeren, dann laeuft es mit bestellsystem/dev-server.mjs.
// Bestellen kann nur, wer einen gueltigen Code im Link hat; ohne Code bleibt die Karte eine Lesekarte.
// Der key ist der oeffentliche (publishable) Schluessel und darf im Browser stehen.
window.NANNI = {
  url: 'https://tiylkcjxpsybylnbzakd.supabase.co',
  key: 'sb_publishable_erVLj0RslYDUTxXme9JNQw_JTHhHaE7',
  async rpc(fn, args) {
    const headers = { 'content-type': 'application/json' };
    if (this.key) { headers.apikey = this.key; headers.authorization = 'Bearer ' + this.key; }
    const res = await fetch(this.url + '/rest/v1/rpc/' + fn, { method: 'POST', headers, body: JSON.stringify(args || {}), cache: 'no-store' });
    if (!res.ok) throw new Error('rpc ' + fn + ' ' + res.status);
    return res.json();
  }
};
