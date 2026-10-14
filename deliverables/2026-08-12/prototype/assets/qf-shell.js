/* ============================================================
   QualityForge 原型交互脚本 (qf-shell.js)
   - 弹窗: openModal / closeModal (ESC + 遮罩 + ×)
   - Toast: showToast
   - 导航高亮: 按 body[data-page] 自动激活侧栏
   - 本地持久化: qf.store (localStorage) — 表单提交/刷新复核
   - 演示数据: 新建工作项 / 登录会话
   ============================================================ */
(function () {
  'use strict';

  /* ---------- 弹窗 ---------- */
  function openModal(id) {
    var m = document.getElementById(id);
    if (!m) return;
    m.classList.add('open');
    document.body.style.overflow = 'hidden';
    if (document.activeElement) window.__qfLastFocus = document.activeElement;
    var box = m.querySelector('.modal-box');
    if (box) {
      var h3 = box.querySelector('.modal-head h3');
      if (h3) {
        if (!h3.id) h3.id = m.id + '-title';
        box.setAttribute('aria-labelledby', h3.id);
      }
      setTimeout(function () { box.focus && box.focus(); }, 50);
    }
    if (typeof window.__qfOnOpen === 'function') window.__qfOnOpen(id);
  }
  function closeModal(id) {
    var m = document.getElementById(id);
    if (!m) return;
    m.classList.remove('open');
    if (!document.querySelector('.modal.open')) {
      document.body.style.overflow = '';
      if (window.__qfLastFocus && window.__qfLastFocus.focus) window.__qfLastFocus.focus();
    }
  }
  function closeTopModal() {
    var list = document.querySelectorAll('.modal.open');
    if (list.length) closeModal(list[list.length - 1].id);
  }
  document.addEventListener('click', function (e) {
    if (e.target.classList && e.target.classList.contains('modal')) closeModal(e.target.id);
    if (e.target.closest && e.target.closest('.modal-close')) {
      var m = e.target.closest('.modal');
      if (m) closeModal(m.id);
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeTopModal();
  });

  /* ---------- Toast ---------- */
  function showToast(msg, type) {
    var wrap = document.querySelector('.toast-wrap');
    if (!wrap) { wrap = document.createElement('div'); wrap.className = 'toast-wrap'; document.body.appendChild(wrap); }
    var t = document.createElement('div');
    t.className = 'toast ' + (type || 'info');
    t.innerHTML = '<span class="t-dot"></span>' + msg;
    wrap.appendChild(t);
    setTimeout(function () { t.style.opacity = '0'; t.style.transition = 'opacity .25s'; }, 2600);
    setTimeout(function () { t.remove(); }, 3000);
  }

  /* ---------- 导航高亮 ---------- */
  document.addEventListener('DOMContentLoaded', function () {
    var page = document.body.getAttribute('data-page') || '';
    document.querySelectorAll('.nav-item').forEach(function (n) {
      if (n.getAttribute('data-nav') === page) n.classList.add('active');
    });
    document.querySelectorAll('[data-link]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        var href = a.getAttribute('href');
        if (href && href.indexOf('.html') > -1) return; // 真实跳转
      });
    });
    initNavDrawer();
    // P1-3 修复: 可点击表格行键盘可达(Enter 触发点击)
    document.querySelectorAll('tbody tr[onclick]').forEach(function (row) {
      row.setAttribute('tabindex', '0');
      row.setAttribute('role', 'button');
      row.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); row.click(); }
      });
    });
    // P1-3 修复: 弹窗焦点圈定(打开时圈定, 关闭时返回触发元素)
    var lastFocus = null;
    document.addEventListener('click', function (e) {
      var opener = e.target.closest('[onclick*="openModal"]');
      if (opener) lastFocus = opener;
    });
    var focusModal = function (m) {
      var focusables = m.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (focusables.length) focusables[0].focus();
    };
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      var open = document.querySelector('.modal.open');
      if (!open) return;
      var focusables = open.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (!focusables.length) return;
      var first = focusables[0], last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    // 关闭时恢复焦点
    var origClose = window.qf ? window.qf.closeModal : null;
  });

  /* ---------- 明暗主题 (tokens 已定义 [data-theme=dark], 这里负责应用+切换+持久化) ---------- */
  var THEME_KEY = 'qf.theme';
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t === 'dark' ? 'dark' : 'light');
    var btn = document.querySelector('.theme-toggle');
    if (btn) { btn.setAttribute('aria-pressed', t === 'dark'); btn.setAttribute('title', t === 'dark' ? '切换到亮色' : '切换到暗色'); btn.innerHTML = t === 'dark' ? '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="8" cy="8" r="3.4"/><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.3 3.3l1.4 1.4M11.3 11.3l1.4 1.4M12.7 3.3l-1.4 1.4M4.7 11.3l-1.4 1.4"/></svg>' : '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13.5 9.5A6 6 0 1 1 6.5 2.5a4.8 4.8 0 0 0 7 7Z"/></svg>';
  }
  function currentTheme() { return document.documentElement.getAttribute('data-theme') || (store.get(THEME_KEY, null) || 'light'); }
  function toggleTheme() { var next = currentTheme() === 'dark' ? 'light' : 'dark'; store.set(THEME_KEY, next); applyTheme(next); }
  function initTheme() {
    var saved = store.get(THEME_KEY, null);
    if (!saved) saved = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
    applyTheme(saved);
    var topbar = document.querySelector('.topbar');
    var host = topbar ? topbar : document.querySelector('.login-wrap') || document.body;
    if (document.querySelector('.theme-toggle')) return;
    var btn = document.createElement('button');
    btn.className = 'theme-toggle';
    btn.setAttribute('aria-label', '切换明暗主题');
    btn.setAttribute('aria-pressed', saved === 'dark');
    btn.title = saved === 'dark' ? '切换到亮色' : '切换到暗色';
    btn.addEventListener('click', toggleTheme);
    if (topbar) { topbar.appendChild(btn); }
    else { document.body.appendChild(btn); }
    applyTheme(saved);
  }
  function toggleTheme() { toggleTheme = function(){}; toggleTheme(); }
}

  /* ---------- 本地存储 ---------- */
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem('qf.' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem('qf.' + k, JSON.stringify(v)); } catch (e) {} },
    remove: function (k) { try { localStorage.removeItem('qf.' + k); } catch (e) {} }
  };

  /* ---------- H4 修复: 移动端导航抽屉 ---------- */
  function initNavDrawer() {
    var sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    var topbar = document.querySelector('.topbar');
    if (!topbar) return;
    if (document.querySelector('.nav-hamburger')) return;
    var hamburger = document.createElement('button');
    hamburger.className = 'nav-hamburger';
    hamburger.setAttribute('aria-label', '打开导航');
    hamburger.innerHTML = '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 4h12M2 8h12M2 12h12"/></svg>';
    topbar.insertBefore(hamburger, topbar.firstChild);
    var drawer = document.createElement('div');
    drawer.className = 'nav-drawer';
    drawer.setAttribute('aria-label', '主导航');
    drawer.innerHTML = sidebar.innerHTML;
    var mask = document.createElement('div');
    mask.className = 'nav-drawer-mask';
    document.body.appendChild(drawer);
    document.body.appendChild(mask);
    function openDrawer() { drawer.classList.add('open'); mask.classList.add('open'); }
    function closeDrawer() { drawer.classList.remove('open'); mask.classList.remove('open'); }
    hamburger.addEventListener('click', openDrawer);
    mask.addEventListener('click', closeDrawer);
    drawer.querySelectorAll('.nav-item').forEach(function (b) {
      b.addEventListener('click', function () {
        if (b.getAttribute('onclick') && b.getAttribute('onclick').indexOf('location.href') > -1) closeDrawer();
      });
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDrawer(); });
  }

  /* ---------- 演示: 登录会话 ---------- */
  var session = {
    login: function (name, role) { store.set('session', { name: name, role: role, at: Date.now() }); },
    logout: function () { store.remove('session'); },
    get: function () { return store.get('session', null); }
  };

  /* ---------- 演示: 新建工作项(持久化到 localStorage, 看板页读取) ---------- */
  var items = {
    all: function () { return store.get('myItems', []); },
    add: function (item) {
      var list = store.get('myItems', []);
      item.id = 'WI-' + (9000 + list.length + 1);
      item.createdAt = Date.now();
      item.status = item.status || '待办';
      item.source = 'local';
      list.unshift(item);
      store.set('myItems', list);
      return item;
    },
    remove: function (id) {
      store.set('myItems', store.get('myItems', []).filter(function (i) { return i.id !== id; }));
    }
  };

  /* ---------- 通用: 表单校验演示 ---------- */
  function bindForm(id, onValid) {
    var f = document.getElementById(id);
    if (!f) return;
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var firstErr = null;
      f.querySelectorAll('[required]').forEach(function (el) {
        var field = el.closest('.field');
        // A1 修复: 完整校验 validity (required/pattern/minlength/type)
        var invalid = false;
        if (!el.value || !el.value.trim()) {
          invalid = true;
        } else if (el.validity && (el.validity.patternMismatch || el.validity.typeMismatch || el.validity.tooShort || el.validity.rangeOverflow || el.validity.rangeUnderflow || el.validity.stepMismatch)) {
          invalid = true;
        }
        if (invalid) {
          if (field) field.classList.add('has-err');
          if (!firstErr) firstErr = field || el;
        } else if (field) { field.classList.remove('has-err'); }
      });
      if (firstErr) {
        showToast('请检查必填项', 'err');
        if (firstErr.focus) firstErr.focus();
        if (firstErr.scrollIntoView) firstErr.scrollIntoView({ block: 'center', behavior: 'smooth' });
        return;
      }
      if (onValid) onValid(f);
    });
    f.querySelectorAll('input,select,textarea').forEach(function (el) {
      el.addEventListener('input', function () {
        var field = el.closest('.field');
        if (field && el.value && el.value.trim()) field.classList.remove('has-err');
      });
    });
  }

  /* ---------- 暴露 ---------- */
  window.qf = { openModal: openModal, closeModal: closeModal, toast: showToast, store: store, session: session, items: items, bindForm: bindForm };
})();
