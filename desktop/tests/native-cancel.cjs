// Explicit, no-API desktop diagnostic. Opens Start/search, then kills the input helper.
if (process.env.NODE_TEST_CONTEXT) {
  require('node:test')('native cancellation requires an explicit manual run', { skip: true }, () => {});
} else {
const assert = require('node:assert/strict');
const path = require('node:path');
const { DesktopActions } = require('../actions.cjs');
const root = path.resolve(__dirname, '../..');
let cancelledAtSearch = false;
const controller = new DesktopActions({ root, onState: state => {
  if (state.running && state.label.startsWith('Searching for')) {
    cancelledAtSearch = true;
    controller.stop('native-cancel');
  }
} });
(async () => {
  const result = await controller.run({ kind: 'open_app', appName: 'Notion' }, 'native-cancel');
  assert.equal(cancelledAtSearch, true, 'Expected visible Start/search before cancellation');
  assert.equal(result.status, 'cancelled');
  assert.equal(controller.active, null, 'Input helper must exit before completion');
  console.log('Native cancellation passed: helper exited; no launch was requested.');
})().catch(error => { console.error(error.message); process.exitCode = 1; }).finally(() => controller.shutdown());
}
