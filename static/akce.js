/* kuponmat.cz/akce — filters, sorting, search, favourites and shopping list. No dependencies, localStorage only. */
(function () {
  var BASE = '/akce/';
  function ls(k, v) {
    try {
      if (v === undefined) return JSON.parse(localStorage.getItem(k) || 'null');
      localStorage.setItem(k, JSON.stringify(v));
    } catch (e) { return null; }
  }
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function norm(s) { return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }
  function kc(v) { if (v == null) return ''; var s = v.toFixed(2).replace('.', ','); if (s.slice(-3) === ',00') s = s.slice(0, -3); return s + ' Kč'; }
  function dshort(iso) { var p = iso.split('-'); return (+p[2]) + '. ' + (+p[1]) + '.'; }

  /* ---------- filter + sort on listing pages */
  var tools = $('[data-tools]');
  if (tools) {
    var chain = '';
    var grids = $$('.ka-section:not(.ka-future) .ka-grid').concat($$('.ka-pg-rows'));
    function cmp(key) {
      return function (a, b) {
        if (key === 'disc') return (+b.dataset.disc) - (+a.dataset.disc);
        if (key === 'do') return a.dataset.do < b.dataset.do ? -1 : a.dataset.do > b.dataset.do ? 1 : 0;
        if (key === 'unit') return (+a.dataset.unit || 1e9) - (+b.dataset.unit || 1e9);
        return (+a.dataset.price) - (+b.dataset.price);
      };
    }
    function apply() {
      var key = $('[data-sort]', tools).value;
      grids.forEach(function (g) {
        var cards = $$('.ka-card, .ka-pg-row', g);
        cards.forEach(function (c) { c.hidden = !!chain && c.dataset.chain !== chain; });
        cards.sort(cmp(key)).forEach(function (c) { g.appendChild(c); });
      });
      // product blocks: hide those without a visible row, order by their best visible row
      var box = $('.ka-pgs');
      if (box) {
        var blocks = $$('.ka-pg', box);
        blocks.forEach(function (p) { p.hidden = !$$('.ka-pg-row', p).some(function (r) { return !r.hidden; }); });
        if (key !== 'price' || chain) blocks.sort(function (a, b) {
          var ra = $$('.ka-pg-row', a).filter(function (r) { return !r.hidden; })[0], rb = $$('.ka-pg-row', b).filter(function (r) { return !r.hidden; })[0];
          if (!ra || !rb) return ra ? -1 : rb ? 1 : 0;
          return cmp(key)(ra, rb);
        }).forEach(function (p) { box.appendChild(p); });
      }
    }
    $$('[data-view]').forEach(function (b) {
      b.addEventListener('click', function () {
        $$('[data-view]').forEach(function (x) { x.classList.toggle('on', x === b); });
        $$('[data-pane]').forEach(function (p) { p.hidden = p.dataset.pane !== b.dataset.view; });
      });
    });
    $$('.ka-filter button', tools).forEach(function (b) {
      b.addEventListener('click', function () {
        chain = b.dataset.chain;
        $$('.ka-filter button', tools).forEach(function (x) { x.classList.toggle('on', x === b); });
        apply();
      });
    });
    $('[data-sort]', tools).addEventListener('change', apply);
    var want = new URLSearchParams(location.search).get('obchod');
    if (want) $$('.ka-filter button', tools).forEach(function (b) { if (b.dataset.chain === want) b.click(); });
  }

  /* ---------- shopping list (offer ids) */
  var list = ls('ka-list') || {};
  function syncList() {
    var n = Object.keys(list).length;
    $$('.ka-list-count').forEach(function (e) { e.textContent = n; e.hidden = !n; });
    $$('[data-add]').forEach(function (b) {
      var on = !!list[b.dataset.add];
      b.classList.toggle('on', on);
      b.textContent = b.closest('.ka-pg-row') ? (on ? '✓' : '+') : (on ? '✓ v seznamu' : '+ seznam');
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-add]');
    if (!b) return;
    var id = b.dataset.add, card = b.closest('.ka-card, .ka-pg-row');
    if (list[id]) delete list[id];
    else list[id] = { n: ($('.ka-name', card) || $('.ka-pg-name', card)).textContent.trim(), c: card.dataset.chain, p: +card.dataset.price, d: card.dataset.do };
    ls('ka-list', list); syncList();
  });
  syncList();

  /* ---------- favourites (product keys) */
  var favs = ls('ka-favs') || {};
  $$('[data-fav]').forEach(function (b) {
    var k = b.dataset.fav;
    function paint() { b.classList.toggle('on', !!favs[k]); b.textContent = (favs[k] ? '★ Sleduji ' : '☆ Sledovat ') + b.dataset.name; }
    b.addEventListener('click', function () { if (favs[k]) delete favs[k]; else favs[k] = b.dataset.name; ls('ka-favs', favs); paint(); });
    paint();
  });

  /* ---------- index.json for search + favourites page */
  function loadIndex(cb) {
    fetch(BASE + 'index.json', { cache: 'default' }).then(function (r) { return r.json(); }).then(cb).catch(function () {});
  }
  function cardHtml(r) {
    // [id, name, chain, price, old, pack, od, do, img, typ, produkt, link, unit, unitName]
    var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
    var disc = r[4] ? Math.round((1 - r[3] / r[4]) * 100) : 0;
    return '<article class="ka-card" data-chain="' + esc(r[2]) + '" data-price="' + r[3] + '" data-do="' + r[7] + '">' +
      '<div class="ka-img">' + (r[8] ? '<img src="' + esc(r[8]) + '" alt="' + esc(r[1]) + '" loading="lazy" width="160" height="160">' : '<span class="ka-noimg">' + esc(r[2]) + '</span>') +
      (disc > 0 ? '<span class="ka-badge">−' + disc + ' %</span>' : '') + '</div>' +
      '<div class="ka-body"><span class="ka-chain">' + esc(r[2]) + '</span><h3 class="ka-name">' + esc(r[1]) + '</h3>' +
      (r[5] ? '<div class="ka-pack">' + esc(r[5]) + '</div>' : '') +
      '<div class="ka-price"><strong>' + kc(r[3]) + '</strong>' + (r[4] ? ' <s>' + kc(r[4]) + '</s>' : '') + '</div>' +
      (r[12] && r[13] ? '<div class="ka-unit">' + kc(r[12]) + ' / ' + esc(r[13]) + '</div>' : '') +
      '<div class="ka-valid">do ' + dshort(r[7]) + '</div><div class="ka-actions">' +
      (r[11] ? '<a class="ka-src" href="' + esc(r[11]) + '">Zdroj ›</a>' : '') +
      (r[10] ? '<a class="ka-src" href="' + BASE + esc(r[10]) + '/">Srovnat ›</a>' : (r[9] ? '<a class="ka-src" href="' + BASE + esc(r[9]) + '/">Srovnat ›</a>' : '')) +
      '<button type="button" class="ka-add" data-add="' + esc(r[0]) + '">+ seznam</button></div></div></article>';
  }

  var res = $('[data-search-results]');
  if (res) {
    var q = new URLSearchParams(location.search).get('q') || '';
    var inp = $('.ka-search input'); if (inp) inp.value = q;
    if (q) loadIndex(function (ix) {
      var words = norm(q).split(/\s+/).filter(Boolean);
      var hits = ix.o.filter(function (r) { var t = norm(r[1] + ' ' + r[2] + ' ' + r[9]); return words.every(function (w) { return t.indexOf(w) >= 0; }); });
      hits.sort(function (a, b) { return a[3] - b[3]; });
      $('[data-search-info]').textContent = hits.length ? ('Nalezeno ' + hits.length + ' akcí pro „' + q + '“.') : ('Pro „' + q + '“ teď žádnou akci nemáme.');
      res.innerHTML = hits.slice(0, 200).map(cardHtml).join('');
      syncList();
    });
  }

  var favBox = $('[data-favs]'), listBox = $('[data-list]');
  if (favBox || listBox) loadIndex(function (ix) {
    var today = ix.d;
    var keys = Object.keys(favs);
    if (keys.length) {
      $('[data-favs-empty]').hidden = true;
      var hits = ix.o.filter(function (r) { return keys.indexOf(r[10]) >= 0 || keys.indexOf(r[9]) >= 0; });
      favBox.innerHTML = keys.map(function (k) { return '<a class="ka-chip" href="' + BASE + k + '/">' + favs[k] + '</a>'; }).join(' ') + hits.map(cardHtml).join('');
    }
    var ids = Object.keys(list);
    if (ids.length) {
      $('[data-list-clear]').hidden = false;
      var total = 0;
      listBox.innerHTML = ids.map(function (id) {
        var it = list[id], gone = it.d < today; if (!gone) total += it.p;
        return '<div class="ka-list-row' + (gone ? ' gone' : '') + '"><span>' + it.n + ' <small>(' + it.c + (gone ? ', akce skončila' : ', do ' + dshort(it.d)) + ')</small></span><span>' + kc(it.p) + ' <button data-del="' + id + '" aria-label="Odebrat">×</button></span></div>';
      }).join('') + '<div class="ka-list-row"><b>Celkem (platné akce)</b><b>' + kc(total) + '</b></div>';
    }
    syncList();
  });
  document.addEventListener('click', function (e) {
    var d = e.target.closest && e.target.closest('[data-del]');
    if (d) { delete list[d.dataset.del]; ls('ka-list', list); location.reload(); }
    var c = e.target.closest && e.target.closest('[data-list-clear]');
    if (c) { list = {}; ls('ka-list', list); location.reload(); }
  });
})();
