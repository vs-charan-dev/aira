import test from 'node:test';
import assert from 'node:assert/strict';
import { invoiceTotal } from './invoice.js';

test('10% discount on 200 gives 180', () => assert.equal(invoiceTotal(200, 10), 180));
test('no discount keeps the price', () => assert.equal(invoiceTotal(200, 0), 200));
test('100% discount makes the invoice free', () => assert.equal(invoiceTotal(200, 100), 0));
test('25% discount on 80 gives 60', () => assert.equal(invoiceTotal(80, 25), 60));
test('fractional discount is supported', () => assert.equal(invoiceTotal(120, 12.5), 105));
