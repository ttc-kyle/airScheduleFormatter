(function () {
  'use strict';

  var STORE_KEY = 'emailFormatter.draft.v1';
  var BASE_STYLE = 'font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.5;color:#222222;';
  var P_STYLE = 'margin:0 0 12px 0;';
  var LIST_STYLE = 'margin:0 0 12px 0;padding-left:24px;';

  function lhCss(lh) { return lh ? 'line-height:' + lh + ';' : ''; }
  function pStyle(lh) { return P_STYLE + lhCss(lh); }
  // Only plain unitless multipliers from 1 to 3 survive; anything else falls back to the default.
  function safeLh(v) {
    v = (v || '').trim();
    var n = parseFloat(v);
    return /^\d*\.?\d+$/.test(v) && n >= 1 && n <= 3 ? String(n) : '';
  }

  var DEFAULT_COLOR = '#222222';
  // Accepts #rgb, #rrggbb and rgb()/rgba(); returns lowercase #rrggbb, or '' for anything else (named colors, url(), etc.).
  function safeColor(v) {
    v = (v || '').trim().toLowerCase();
    var m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/.exec(v);
    if (m) return m[1].length === 3 ? '#' + m[1].replace(/./g, '$&$&') : v;
    m = /^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*[\d.]+\s*)?\)$/.exec(v);
    if (!m) return '';
    return '#' + [m[1], m[2], m[3]].map(function (n) { return ('0' + Math.min(255, +n).toString(16)).slice(-2); }).join('');
  }
  var allowColor = true;

  var DEFAULT_SIZE = 14;
  // Only whole-number px sizes from 10 to 40 survive; anything else is dropped.
  function safeSize(v) {
    var m = /^(\d{1,2})(?:\.\d+)?px$/.exec((v || '').trim().toLowerCase());
    var n = m ? parseInt(m[1], 10) : 0;
    return n >= 10 && n <= 40 ? n : 0;
  }
  var allowSize = true;

  var $ = function (id) { return document.getElementById(id); };
  var editor = $('editor'), subjectEl = $('subject');
  var generatedHtml = '';
  var savedRange = null;

  /* ---------- Sanitizer / serializer ---------- */

  var DROP = { SCRIPT: 1, STYLE: 1, META: 1, LINK: 1, HEAD: 1, TITLE: 1, IFRAME: 1, OBJECT: 1, NOSCRIPT: 1 };
  var BLOCK = { P: 1, DIV: 1, UL: 1, OL: 1, LI: 1, H1: 1, H2: 1, H3: 1, H4: 1, H5: 1, H6: 1, BLOCKQUOTE: 1, TABLE: 1, TR: 1, PRE: 1 };

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function safeHref(href) {
    href = (href || '').trim();
    if (/^(https?:|mailto:)/i.test(href)) return href;
    if (/^[\w.+-]+@[\w-]+\.[\w.-]+$/.test(href)) return 'mailto:' + href;
    if (/^[\w-]+(\.[\w-]+)+(\/\S*)?$/.test(href)) return 'https://' + href;
    return '';
  }

  function safeSrc(src) {
    src = (src || '').trim();
    if (/^https?:\/\/\S+$/i.test(src)) return src;
    if (/^data:image\/(png|jpe?g|gif|webp);base64,[A-Za-z0-9+\/=]+$/i.test(src)) return src;
    return '';
  }

  function hasBlockChild(el) {
    for (var i = 0; i < el.children.length; i++) if (BLOCK[el.children[i].tagName]) return true;
    return false;
  }

  // Wraps an element's output in a color span. Chrome may put the color on a span, a font tag, or directly on a b/i/u.
  function withColor(node, html) {
    if (!allowColor || !html) return html;
    var c = safeColor(node.tagName === 'FONT' ? node.getAttribute('color') : node.style && node.style.color);
    // The default text color is already set on the wrapper, so it needs no span of its own.
    return c && c !== DEFAULT_COLOR ? '<span style="color:' + c + ';">' + html + '</span>' : html;
  }

  function inline(node) {
    if (node.nodeType === 3) return esc(node.nodeValue.replace(/[\s ]+/g, ' '));
    if (node.nodeType !== 1 || DROP[node.tagName]) return '';
    var inner = kids(node, inline);
    return withSize(node, withColor(node, inlineTag(node, inner)));
  }

  // Wraps an element's output in a font-size span. The default size is already set on the wrapper, so it needs no span.
  function withSize(node, html) {
    if (!allowSize || !html) return html;
    var s = safeSize(node.style && node.style.fontSize);
    return s && s !== DEFAULT_SIZE ? '<span style="font-size:' + s + 'px;">' + html + '</span>' : html;
  }

  function inlineTag(node, inner) {
    switch (node.tagName) {
      case 'B': case 'STRONG': return inner ? '<strong>' + inner + '</strong>' : '';
      case 'I': case 'EM': return inner ? '<em>' + inner + '</em>' : '';
      case 'U': return inner ? '<u>' + inner + '</u>' : '';
      case 'BR': return '<br>';
      case 'IMG':
        var src = safeSrc(node.getAttribute('src'));
        if (!src) return '';
        var w = parseInt(node.getAttribute('width'), 10);
        return '<img src="' + esc(src) + '" alt="' + esc(node.getAttribute('alt') || '') + '"' +
          (w > 0 && w <= 1200 ? ' width="' + w + '"' : '') +
          ' style="border:0;outline:none;max-width:100%;height:auto;">';
      case 'A':
        var href = safeHref(node.getAttribute('href'));
        return href ? '<a href="' + esc(href) + '" style="color:#1a0dab;text-decoration:underline;">' + inner + '</a>' : inner;
      default: return inner;
    }
  }

  function kids(node, fn) {
    var out = '';
    for (var i = 0; i < node.childNodes.length; i++) out += fn(node.childNodes[i]);
    return out;
  }

  function isBlank(html) {
    return html.replace(/<br>/g, '').replace(/&nbsp;/g, '').trim() === '';
  }

  function blocks(container, lh) {
    var out = '', run = '';
    function flush() {
      if (!isBlank(run)) out += '<p style="' + pStyle(lh) + '">' + run.replace(/^(\s|<br>)+|(\s|<br>)+$/g, '') + '</p>';
      run = '';
    }
    for (var i = 0; i < container.childNodes.length; i++) {
      var n = container.childNodes[i];
      if (n.nodeType === 1 && DROP[n.tagName]) continue;
      if (n.nodeType === 1 && BLOCK[n.tagName]) {
        flush();
        out += block(n, lh);
      } else {
        run += inline(n);
      }
    }
    flush();
    return out;
  }

  function block(el, lh) {
    var own = safeLh(el.style && el.style.lineHeight) || lh;
    switch (el.tagName) {
      case 'UL': case 'OL':
        var tag = el.tagName.toLowerCase(), items = '';
        for (var i = 0; i < el.children.length; i++) {
          var li = el.children[i];
          if (li.tagName !== 'LI') continue;
          var body = hasBlockChild(li) ? blocks(li, own).replace(/<p style="[^"]*">/g, '').replace(/<\/p>/g, '<br>').replace(/(<br>)+$/, '') : inline(li);
          if (!isBlank(body)) items += '<li style="margin:0 0 4px 0;' + lhCss(own) + '">' + body + '</li>';
        }
        return items ? '<' + tag + ' style="' + LIST_STYLE + lhCss(own) + '">' + items + '</' + tag + '>' : '';
      case 'LI': return '<p style="' + pStyle(own) + '">' + inline(el) + '</p>';
      default:
        if (hasBlockChild(el)) return blocks(el, own);
        var html = kids(el, inline);
        if (/^H[1-6]$/.test(el.tagName) && !isBlank(html)) html = '<strong>' + html + '</strong>';
        return isBlank(html) ? '' : '<p style="' + pStyle(own) + '">' + html.replace(/^(\s|<br>)+|(\s|<br>)+$/g, '') + '</p>';
    }
  }

  // keepColor=false drops text colors, used for content pasted in from outside the editor.
  function sanitizeFragment(html, keepColor) {
    var doc = new DOMParser().parseFromString(html, 'text/html');
    var prev = allowColor, prevSize = allowSize;
    allowColor = allowSize = keepColor !== false;
    try { return blocks(doc.body, ''); } finally { allowColor = prev; allowSize = prevSize; }
  }

  /* ---------- Draft persistence ---------- */

  // Drafts live in sessionStorage (cleared when the tab closes) and expire after DRAFT_TTL_MS,
  // so a draft never outlives the agent's session or carries over to the next person.
  var DRAFT_TTL_MS = 45 * 60 * 1000;

  // Remove drafts left in localStorage by earlier versions that persisted indefinitely.
  try { localStorage.removeItem(STORE_KEY); } catch (e) { /* ignore */ }

  function save() {
    try {
      sessionStorage.setItem(STORE_KEY, JSON.stringify({ subject: subjectEl.value, body: editor.innerHTML, savedAt: Date.now() }));
      $('saved').textContent = 'Saved in this tab for 45 min';
    } catch (e) { $('saved').textContent = ''; }
  }

  function restore() {
    try {
      var d = JSON.parse(sessionStorage.getItem(STORE_KEY) || 'null');
      if (!d) return;
      if (!d.savedAt || Date.now() - d.savedAt > DRAFT_TTL_MS) {
        sessionStorage.removeItem(STORE_KEY);
        return;
      }
      subjectEl.value = d.subject || '';
      editor.innerHTML = sanitizeFragment(d.body || '');
    } catch (e) { /* storage unavailable */ }
  }

  /* ---------- Editor commands ---------- */

  function exec(cmd, val) {
    editor.focus();
    document.execCommand(cmd, false, val || null);
    refreshToolbar();
    onChange();
  }

  function refreshToolbar() {
    document.querySelectorAll('.tool[data-cmd]').forEach(function (b) {
      var on = false;
      try { on = document.queryCommandState(b.dataset.cmd); } catch (e) { /* ignore */ }
      b.classList.toggle('is-on', on);
    });
    var cur = currentLineHeight();
    lsMenu.querySelectorAll('button').forEach(function (b) { b.classList.toggle('is-on', b.dataset.lh === cur); });
    var curSize = currentFontSize();
    fsMenu.querySelectorAll('button').forEach(function (b) { b.classList.toggle('is-on', +b.dataset.fs === curSize); });
    var c = DEFAULT_COLOR;
    try { c = safeColor(document.queryCommandValue('foreColor')) || c; } catch (e) { /* ignore */ }
    // Uncolored text reports the editor's own CSS color, which maps to the output default.
    if (c === safeColor(getComputedStyle(editor).color)) c = DEFAULT_COLOR;
    setColorUi(c);
  }

  document.querySelectorAll('.tool').forEach(function (b) {
    b.addEventListener('mousedown', function (e) { e.preventDefault(); });
  });
  document.querySelectorAll('.tool[data-cmd]').forEach(function (b) {
    b.addEventListener('click', function () { exec(b.dataset.cmd); });
  });
  var lastRange = null;
  document.addEventListener('selectionchange', function () {
    var sel = window.getSelection();
    if (sel.rangeCount && editor.contains(sel.anchorNode)) {
      lastRange = sel.getRangeAt(0).cloneRange();
      refreshToolbar();
    }
  });

  /* Line spacing: stored as a unitless line-height on each top-level block */
  var lsBtn = $('ls-btn'), lsMenu = $('ls-menu');

  function isBlockEl(n) { return n.nodeType === 1 && /^(P|DIV|UL|OL|H[1-6]|BLOCKQUOTE|PRE)$/.test(n.tagName); }

  function topBlock(node) {
    while (node && node.parentNode !== editor) node = node.parentNode;
    return node;
  }

  function currentLineHeight() {
    var sel = window.getSelection();
    if (!sel.rangeCount || !editor.contains(sel.anchorNode)) return '';
    var b = topBlock(sel.anchorNode);
    return b && b.nodeType === 1 ? safeLh(b.style.lineHeight) : '';
  }

  function setLh(el, val) {
    if (val) { el.style.lineHeight = val; return; }
    el.style.removeProperty('line-height');
    if (!el.getAttribute('style')) el.removeAttribute('style');
  }

  function hasContent(n) {
    return n.nodeType === 1 ? (n.tagName === 'IMG' || n.textContent.trim() !== '') : n.nodeValue.trim() !== '';
  }

  function applyLineHeight(val) {
    var range = lastRange;
    if (!range) { range = document.createRange(); range.selectNodeContents(editor); }
    var nodes = Array.prototype.slice.call(editor.childNodes), i = 0;
    while (i < nodes.length) {
      var n = nodes[i];
      if (isBlockEl(n)) {
        if (range.intersectsNode(n)) setLh(n, val);
        i++;
        continue;
      }
      // Loose text and inline nodes directly under the editor become one paragraph so they can carry spacing.
      var run = [n], hit = range.intersectsNode(n);
      i++;
      while (i < nodes.length && !isBlockEl(nodes[i])) {
        hit = hit || range.intersectsNode(nodes[i]);
        run.push(nodes[i++]);
      }
      if (hit && run.some(hasContent)) {
        var p = document.createElement('p');
        editor.insertBefore(p, run[0]);
        run.forEach(function (x) { p.appendChild(x); });
        setLh(p, val);
      }
    }
    editor.focus();
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    refreshToolbar();
    onChange();
  }

  function setMenu(open) {
    lsMenu.hidden = !open;
    lsBtn.setAttribute('aria-expanded', open);
  }
  lsBtn.addEventListener('click', function () { setColorPop(false); setFsMenu(false); setMenu(lsMenu.hidden); });
  lsMenu.querySelectorAll('button').forEach(function (b) {
    b.addEventListener('mousedown', function (e) { e.preventDefault(); });
    b.addEventListener('click', function () { setMenu(false); applyLineHeight(b.dataset.lh); });
  });

  /* Font size: Chrome's fontSize command emits a span with a size keyword; each new span is rewritten to the chosen px size. */
  var fsBtn = $('fs-btn'), fsMenu = $('fs-menu');
  var pendingSize = DEFAULT_SIZE;

  function setFsMenu(open) {
    fsMenu.hidden = !open;
    fsBtn.setAttribute('aria-expanded', open);
  }

  function currentFontSize() {
    var sel = window.getSelection();
    if (!sel.rangeCount || !editor.contains(sel.anchorNode)) return 0;
    var el = sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentNode;
    return Math.round(parseFloat(getComputedStyle(el).fontSize)) || 0;
  }

  // Style-only rewrite (no node moves), so the selection and caret are untouched.
  function normalizeSizes() {
    editor.querySelectorAll('span[style*="font-size"]').forEach(function (s) {
      if (s.style.fontSize.indexOf('xxx-large') !== -1) s.style.fontSize = pendingSize + 'px';
    });
    // With nothing selected, Chrome wraps the next typed text in <font size="7"> instead of a span.
    editor.querySelectorAll('font[size="7"]').forEach(function (f) { f.style.fontSize = pendingSize + 'px'; });
  }

  function applyFontSize(px) {
    pendingSize = px;
    editor.focus();
    if (lastRange) {
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(lastRange);
    }
    document.execCommand('styleWithCSS', false, true);
    document.execCommand('fontSize', false, '7');
    document.execCommand('styleWithCSS', false, false);
    normalizeSizes();
    refreshToolbar();
    onChange();
  }

  fsBtn.addEventListener('click', function () { setMenu(false); setColorPop(false); setFsMenu(fsMenu.hidden); });
  fsMenu.querySelectorAll('button').forEach(function (b) {
    b.addEventListener('mousedown', function (e) { e.preventDefault(); });
    b.addEventListener('click', function () { setFsMenu(false); applyFontSize(+b.dataset.fs); });
  });

  document.addEventListener('mousedown', function (e) {
    if (!e.target.closest('.menu-wrap')) { setMenu(false); setFsMenu(false); setColorPop(false); }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { setMenu(false); setFsMenu(false); setColorPop(false); } });

  /* Font color: preset swatches, the browser's native picker, and a hex field */
  var colorBtn = $('color-btn'), colorBar = $('color-bar'), colorPop = $('color-pop');
  var colorNative = $('color-native'), colorHex = $('color-hex'), swatchBox = $('color-swatches');
  var SWATCHES = ['#222222', '#787774', '#C0392B', '#D35400', '#B7950B', '#2E8B57', '#1F6C9F', '#2C3E91', '#7D3C98', '#000000'];

  SWATCHES.forEach(function (hex) {
    var s = document.createElement('button');
    s.type = 'button';
    s.className = 'swatch';
    s.dataset.color = hex.toLowerCase();
    s.style.background = hex;
    s.title = hex === DEFAULT_COLOR.toUpperCase() ? 'Default (' + hex + ')' : hex;
    s.setAttribute('aria-label', s.title);
    s.addEventListener('click', function () { applyColor(hex); });
    swatchBox.appendChild(s);
  });

  function setColorPop(open) {
    colorPop.hidden = !open;
    colorBtn.setAttribute('aria-expanded', open);
  }

  // Reflects a color in the ribbon button, the swatches, the native picker and the hex field.
  function setColorUi(hex) {
    colorBar.style.background = hex;
    colorNative.value = hex;
    if (document.activeElement !== colorHex) { colorHex.value = hex.toUpperCase(); colorHex.classList.remove('invalid'); }
    swatchBox.querySelectorAll('.swatch').forEach(function (s) { s.classList.toggle('is-on', s.dataset.color === hex); });
  }

  function applyColor(input) {
    var hex = safeColor(/^[0-9a-f]{3}([0-9a-f]{3})?$/i.test(input.trim()) ? '#' + input.trim() : input);
    colorHex.classList.toggle('invalid', !hex);
    if (!hex) return;
    editor.focus();
    if (lastRange) {
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(lastRange);
    }
    // Emit a styled span, then switch back so Bold/Italic keep producing <b>/<i> tags.
    document.execCommand('styleWithCSS', false, true);
    document.execCommand('foreColor', false, hex);
    document.execCommand('styleWithCSS', false, false);
    setColorUi(hex);
    setColorPop(false);
    onChange();
  }

  colorBtn.addEventListener('click', function () { setMenu(false); setFsMenu(false); setColorPop(colorPop.hidden); });
  // The native picker fires input continuously while dragging; only commit when it closes.
  colorNative.addEventListener('input', function () { colorHex.value = colorNative.value.toUpperCase(); colorHex.classList.remove('invalid'); });
  colorNative.addEventListener('change', function () { applyColor(colorNative.value); });
  colorHex.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); applyColor(colorHex.value); } });
  colorHex.addEventListener('input', function () {
    var v = colorHex.value.trim();
    var hex = safeColor(/^[0-9a-f]{3}([0-9a-f]{3})?$/i.test(v) ? '#' + v : v);
    colorHex.classList.toggle('invalid', v !== '' && v.replace('#', '').length >= 6 && !hex);
    if (hex) colorNative.value = hex;
  });
  $('color-apply').addEventListener('click', function () { applyColor(colorHex.value); });

  /* Link bar */
  var linkbar = $('linkbar'), linkUrl = $('link-url');

  function openLinkBar() {
    var sel = window.getSelection();
    savedRange = sel.rangeCount && editor.contains(sel.anchorNode) ? sel.getRangeAt(0).cloneRange() : null;
    linkbar.hidden = false;
    linkUrl.value = '';
    linkUrl.focus();
  }
  function closeLinkBar() {
    linkbar.hidden = true;
    editor.focus();
    if (savedRange) {
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(savedRange);
    }
  }
  $('link-btn').addEventListener('click', openLinkBar);
  $('link-cancel').addEventListener('click', closeLinkBar);
  linkbar.addEventListener('submit', function (e) {
    e.preventDefault();
    var href = safeHref(linkUrl.value);
    closeLinkBar();
    if (!href) return;
    var sel = window.getSelection();
    if (sel.isCollapsed) document.execCommand('insertHTML', false, '<a href="' + esc(href) + '">' + esc(linkUrl.value.trim()) + '</a>');
    else document.execCommand('createLink', false, href);
    onChange();
  });

  editor.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openLinkBar(); }
  });

  var internalCopy = '';
  ['copy', 'cut'].forEach(function (evt) {
    editor.addEventListener(evt, function () { internalCopy = window.getSelection().toString().replace(/\s+/g, ' ').trim(); });
  });

  /* Paste: strip to the same whitelist as the output */
  editor.addEventListener('paste', function (e) {
    var cd = e.clipboardData;
    if (!cd) return;
    e.preventDefault();
    var html = cd.getData('text/html');
    // Colors survive when the text was copied from inside the editor; outside content gets plain text color.
    var internal = internalCopy !== '' && cd.getData('text/plain').replace(/\s+/g, ' ').trim() === internalCopy;
    var clean = html ? sanitizeFragment(html, internal) : '';
    var file = firstImage(cd.files);
    if (file && !clean.trim()) {
      insertImageFile(file);
    } else if (clean) {
      document.execCommand('insertHTML', false, clean);
    } else {
      document.execCommand('insertText', false, cd.getData('text/plain'));
    }
    onChange();
  });

  /* ---------- Images ---------- */

  var MAX_IMG_WIDTH = 600;

  function firstImage(files) {
    for (var i = 0; files && i < files.length; i++) if (/^image\/(png|jpe?g|gif|webp)$/i.test(files[i].type)) return files[i];
    return null;
  }

  // Reads the file, shrinks it to MAX_IMG_WIDTH if wider, and inserts it at the caret as a data URI.
  function insertImageFile(file) {
    var reader = new FileReader();
    reader.onload = function () {
      var img = new Image();
      img.onload = function () {
        var src = reader.result, w = img.naturalWidth;
        if (w > MAX_IMG_WIDTH) {
          var c = document.createElement('canvas');
          c.width = MAX_IMG_WIDTH;
          c.height = Math.round(img.naturalHeight * MAX_IMG_WIDTH / w);
          c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
          src = c.toDataURL(file.type === 'image/jpeg' ? 'image/jpeg' : 'image/png', 0.85);
          w = MAX_IMG_WIDTH;
        }
        editor.focus();
        document.execCommand('insertHTML', false, '<img src="' + src + '" alt="" width="' + w + '">');
        onChange();
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  }

  $('img-btn').addEventListener('click', function () {
    var sel = window.getSelection();
    savedRange = sel.rangeCount && editor.contains(sel.anchorNode) ? sel.getRangeAt(0).cloneRange() : null;
    $('img-input').click();
  });
  $('img-input').addEventListener('change', function (e) {
    var file = firstImage(e.target.files);
    e.target.value = '';
    if (!file) return;
    editor.focus();
    if (savedRange) {
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(savedRange);
    }
    insertImageFile(file);
  });

  editor.addEventListener('dragover', function (e) {
    if (firstImage(e.dataTransfer && e.dataTransfer.files)) e.preventDefault();
  });
  editor.addEventListener('drop', function (e) {
    var file = firstImage(e.dataTransfer && e.dataTransfer.files);
    if (!file) return;
    e.preventDefault();
    if (document.caretRangeFromPoint) {
      var r = document.caretRangeFromPoint(e.clientX, e.clientY);
      if (r) { var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r); }
    }
    insertImageFile(file);
  });

  /* ---------- Output ---------- */

  function build() {
    var body = blocks(editor, '');
    var head = '';
    if ($('inc-subject').checked && subjectEl.value.trim()) {
      head = '<p style="' + P_STYLE + '"><strong>Subject:</strong> ' + esc(subjectEl.value.trim()) + '</p>';
    }
    return '<div style="' + BASE_STYLE + '">' + head + body + '</div>';
  }

  function pretty(html) {
    return html.replace(/(<\/p>|<\/ul>|<\/ol>|<\/li>)(?=<)/g, '$1\n').replace(/(<ul[^>]*>|<ol[^>]*>)(?=<li)/g, '$1\n');
  }

  function render() {
    generatedHtml = build();
    $('preview').innerHTML = generatedHtml;
    // Long base64 image data is shortened in this view only; Copy uses the full HTML.
    $('source').textContent = pretty(generatedHtml).replace(/(data:image\/[a-z+]+;base64,)[A-Za-z0-9+\/=]{60,}/gi,
      function (m, head) { return head + m.slice(head.length, head.length + 40) + '...[full image data is included when copied]'; });
  }

  function setTag(el, text, cls) {
    el.textContent = text;
    el.className = 'tag ' + cls;
  }

  // Rebuilds the output from the current draft; shows the empty state when there is no body content.
  function update() {
    var has = editor.textContent.trim() || editor.querySelector('img');
    if (!has) {
      generatedHtml = '';
      $('result').hidden = true;
      $('empty').hidden = false;
      setTag($('out-tag'), 'Waiting', 'tag-blue');
      return;
    }
    render();
    $('empty').hidden = true;
    $('result').hidden = false;
    setTag($('out-tag'), 'Ready', 'tag-green');
  }

  var updateTimer;
  function scheduleUpdate() {
    clearTimeout(updateTimer);
    updateTimer = setTimeout(update, 120);
  }

  $('inc-subject').addEventListener('change', update);

  document.querySelectorAll('.seg').forEach(function (b) {
    b.addEventListener('click', function () {
      var src = b.dataset.view === 'source';
      document.querySelectorAll('.seg').forEach(function (s) {
        var on = s === b;
        s.classList.toggle('is-active', on);
        s.setAttribute('aria-selected', on);
      });
      $('preview').hidden = src;
      $('source').hidden = !src;
    });
  });

  /* ---------- Copy ---------- */

  function flash(msg) {
    var el = $('copied');
    el.textContent = msg;
    el.classList.add('ok');
    clearTimeout(flash.t);
    flash.t = setTimeout(function () { el.textContent = ''; el.classList.remove('ok'); }, 2500);
  }

  function fallbackCopyText(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    var ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  }

  $('copy-rich').addEventListener('click', function () {
    var text = generatedHtml;
    var done = 'Copied. Paste it into your email tool.';
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { flash(done); },
        function () { flash(fallbackCopyText(text) ? done : 'Copy failed.'); });
    } else {
      flash(fallbackCopyText(text) ? done : 'Copy failed.');
    }
  });

  /* ---------- Clear + change tracking ---------- */

  function onChange() {
    normalizeSizes();
    save();
    scheduleUpdate();
  }

  subjectEl.addEventListener('input', onChange);
  editor.addEventListener('input', onChange);

  var confirmDlg = $('confirm-clear');

  $('clear').addEventListener('click', function () {
    if (!editor.textContent.trim() && !editor.querySelector('img') && !subjectEl.value) return;
    confirmDlg.showModal();
  });
  $('confirm-cancel').addEventListener('click', function () { confirmDlg.close(); });
  // Clicking the dimmed backdrop (the dialog element itself) dismisses without clearing.
  confirmDlg.addEventListener('click', function (e) { if (e.target === confirmDlg) confirmDlg.close(); });
  $('confirm-yes').addEventListener('click', function () {
    confirmDlg.close();
    subjectEl.value = '';
    editor.innerHTML = '';
    clearTimeout(updateTimer);
    update();
    try { sessionStorage.removeItem(STORE_KEY); } catch (e) { /* ignore */ }
    $('saved').textContent = '';
  });

  /* ---------- Entry animation ---------- */

  function initReveal() {
    var els = document.querySelectorAll('.reveal');
    if (!('IntersectionObserver' in window)) {
      els.forEach(function (el) { el.classList.add('in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.05 });
    els.forEach(function (el) { io.observe(el); });
  }

  restore();
  update();
  initReveal();
})();
