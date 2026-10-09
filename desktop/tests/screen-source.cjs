const test = require('node:test'), assert = require('node:assert/strict');
const { selectScreen } = require('../screen-source.cjs');
test('uses the monitor under the cursor, never a window or another monitor', () => {
  const sources = [{id:'window:7',display_id:'2'}, {id:'screen:1',display_id:'1'}, {id:'screen:2',display_id:'2'}];
  assert.equal(selectScreen(sources,2).id,'screen:2');
  assert.throws(()=>selectScreen(sources,3),/current monitor/);
  assert.equal(selectScreen([sources[1]],99).id,'screen:1');
  assert.throws(()=>selectScreen([],1));
});
