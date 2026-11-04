'use strict';
(function (root) {
  const columns = Object.freeze(['browser', 'domain', 'name', 'path', 'secure', 'httpOnly', 'sameSite', 'session', 'status', 'expires']);
  function csvCell(value) {
    let text = value === null || value === undefined ? '' : String(value);
    if (/^[\s]*[=+\-@]/.test(text) || /^[\t\r\n]/.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  }
  function metadata(rows) {
    return rows.map(row => Object.fromEntries(columns.map(c => [c, row[c] ?? null])));
  }
  function csv(rows) {
    return '\uFEFF' + [columns.join(','), ...metadata(rows).map(r => columns.map(c => csvCell(r[c])).join(','))].join('\r\n');
  }
  const api = Object.freeze({csvCell, csv, metadata});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CookieReports = api;
})(typeof window !== 'undefined' ? window : {});

