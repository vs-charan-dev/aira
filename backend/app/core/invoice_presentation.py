"""Fixed presentation artifacts shared by backend and native desktop worker."""
import json
import re
from pathlib import Path

REGRESSION_FILE = 'invoice.regression.test.js'
REGRESSION_SOURCE = """// Regression checks written by AIRA for the percentage-discount bug.
import test from 'node:test';
import assert from 'node:assert/strict';
import { invoiceTotal } from './invoice.js';

test('regression: ten percent scales with a larger price', () => assert.equal(invoiceTotal(1000, 10), 900));
test('regression: discount on zero remains zero', () => assert.equal(invoiceTotal(0, 10), 0));
test('regression: decimal prices retain their percentage discount', () => assert.ok(Math.abs(invoiceTotal(99.5, 10) - 89.55) < 1e-9));
"""

def valid_run_id(value):
    return isinstance(value,str) and re.fullmatch(r'[a-f0-9]{32}',value) is not None

def task_payload(root, node, run_id):
    if not valid_run_id(run_id): raise ValueError('Invalid invoice verification run.')
    return {'version':'2.0.0','tasks':[{'label':'AIRA: Verify invoice','type':'process',
        'command':str(Path(node).resolve()),'args':[str(root/'scripts'/'invoice-terminal.cjs'),run_id],
        'options':{'cwd':str(root/'data'/'projects'/'invoice-showcase')},
        'group':{'kind':'build','isDefault':True},
        'presentation':{'reveal':'always','focus':True,'panel':'dedicated','clear':True},'problemMatcher':[]}]}

def validate_task(root, node, value):
    try: run_id=value['tasks'][0]['args'][1]
    except (KeyError,TypeError,IndexError): raise ValueError('Existing VS Code tasks were preserved.') from None
    if value!=task_payload(root,node,run_id): raise ValueError('Existing VS Code tasks were preserved.')
    return run_id

def read_result(root, run_id, version):
    if not valid_run_id(run_id): raise ValueError('Invalid invoice verification run.')
    path=root/'.cache'/'invoice-terminal'/(run_id+'.json')
    if not path.is_file() or path.stat().st_size>4000: raise ValueError('The terminal verification result is missing.')
    result=json.loads(path.read_text(encoding='utf-8'))
    if result.get('runId')!=run_id or result.get('sourceVersion')!=version or not result.get('verified') or result.get('exitCode')!=0 or result.get('tests')!=8 or result.get('passed')!=8:
        raise ValueError('The visible terminal did not verify all eight tests for this source version.')
    return result
