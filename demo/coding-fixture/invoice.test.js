import test from 'node:test';
import assert from 'node:assert/strict';
import { invoiceTotal } from './invoice.js';
test('ten percent discount on 200 is 180', () => assert.equal(invoiceTotal(200, 10), 180));
test('no discount retains price', () => assert.equal(invoiceTotal(200, 0), 200));
test('full discount is free', () => assert.equal(invoiceTotal(200, 100), 0));
