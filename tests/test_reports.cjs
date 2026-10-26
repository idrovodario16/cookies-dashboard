const {test} = require('node:test');
const assert = require('node:assert/strict');
const reports = require('../static/reports.js');

test('formula-like cells are neutralized, including whitespace prefixes', () => {
  for (const value of ['=1+1', '+SUM(1)', '-1+2', '@cmd', '  =1', '\t=1', '\rtest']) {
    assert.ok(reports.csvCell(value).startsWith('"\''));
  }
});
test('CSV handles quotes and commas without changing ordinary metadata', () => {
  assert.equal(reports.csvCell('a,"b"'), '"a,""b"""');
  assert.equal(reports.csvCell(null), '""');
  assert.equal(reports.csvCell('demo.example'), '"demo.example"');
});
test('exports allowlisted fields only, even if unexpected raw fields exist', () => {
  const data = [{domain:'example', name:'n', value:'DO_NOT_EXPORT', encrypted_value:'HIDDEN'}];
  assert.ok(!JSON.stringify(reports.metadata(data)).includes('DO_NOT_EXPORT'));
  assert.ok(!reports.csv(data).includes('HIDDEN'));
  assert.equal(reports.metadata(data)[0].domain, 'example');
});
test('metadata preserves false flags and unknown values', () => {
  const row = reports.metadata([{secure:false, httpOnly:null, session:true}])[0];
  assert.equal(row.secure,false); assert.equal(row.httpOnly,null); assert.equal(row.session,true);
});
