"""Real dispatch functions, with all Win32, browser, editor and history I/O mocked."""
import ast
import io
import json
import sys
import time
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]


def functions(file,names,namespace):
    tree=ast.parse((ROOT/file).read_text(encoding='utf-8'))
    body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert len(body)==len(names)
    exec(compile(ast.Module(body=body,type_ignores=[]),str(ROOT/file),'exec'),namespace)


class ActionError(Exception): pass


class WorkerDispatchTests(unittest.TestCase):
    def test_maps_actions_reach_native_browser_handler(self):
        actions=[{'kind':'open_maps'},{'kind':'search_maps','query':'Hyderabad'}]
        messages,browser,editor,history,native,_=self.serve([dict(action,requestId='maps-'+str(i)) for i,action in enumerate(actions)])
        self.assertEqual([r['status'] for r in messages if r['type']=='result'],['succeeded','succeeded'])
        self.assertEqual([c.args[0] for c in browser.call_args_list],actions)
        editor.assert_not_called()

    def serve(self,requests,gui=False):
        output=io.StringIO()
        native=ModuleType('windows_control')
        native.ActionError=ActionError
        native.user32=SimpleNamespace(SetProcessDPIAware=Mock())
        native.assert_desktop=Mock()
        native.catalog=Mock(return_value=[])
        native.sys=sys
        # Execute the actual native routing function without loading Win32 globals.
        functions('windows_control.py',{'execute'},native.__dict__)
        browser=Mock()
        def browser_execute(api,request):
            browser(request)
            api.emit(type='result',status='succeeded',message='Mocked browser completion')
        browser_module=SimpleNamespace(execute=browser_execute)
        editor=Mock(return_value='Mocked terminal verification')
        history=Mock()
        worker=SimpleNamespace(dependencies=lambda:(native,),run_agent=Mock())
        policy=SimpleNamespace(validate_action=lambda action:action,PolicyError=ActionError)
        namespace={'sys':SimpleNamespace(argv=['--gui'] if gui else [],stdin=io.StringIO(''.join(json.dumps(r)+'\n' for r in requests))),
                   'json':json,'time':time,'PROTOCOL':output}
        functions('action_server.py',{'send','serve'},namespace)
        with patch.dict(sys.modules,{'windows_control':native,'browser_control':browser_module,
                'invoice_control':SimpleNamespace(run_tests_in_editor=editor),
                'desktop_history':SimpleNamespace(History=history),
                'windows_use_worker':worker,'windows_use_policy':policy}):
            namespace['serve']()
        return [json.loads(line) for line in output.getvalue().splitlines()],browser,editor,history,native,worker

    def test_invoice_display_and_terminal_actions_cross_worker_dispatch_with_original_payload(self):
        url='http://127.0.0.1:8000/invoice-demo'
        run='a'*32
        messages,browser,editor,history,native,_=self.serve([
            {'requestId':'demo-open','kind':'show_invoice_demo','url':url},
            {'requestId':'tests-run','kind':'run_invoice_tests','runId':run}])
        self.assertEqual(messages[0]['type'],'ready')
        results=[m for m in messages if m['type']=='result']
        self.assertEqual([(r['requestId'],r['status']) for r in results],[('demo-open','succeeded'),('tests-run','succeeded')])
        browser.assert_called_once_with({'kind':'show_invoice_demo','url':url})
        editor.assert_called_once_with(native,run)
        self.assertEqual(history.call_count,2)
        self.assertEqual(history.return_value.finish.call_count,2)
        self.assertEqual(native.assert_desktop.call_count,2)
        self.assertTrue(all(r['timings']['executionMs']>=0 for r in results))

    def test_unknown_action_and_invalid_request_id_are_rejected_before_native_input(self):
        messages,browser,editor,history,native,_=self.serve([
            {'requestId':'bad-kind','kind':'shell','command':'calc'},
            {'requestId':'../bad-id','kind':'show_invoice_demo','url':'http://127.0.0.1:8000/invoice-demo'}])
        self.assertEqual([m['status'] for m in messages if m['type']=='result'],['failed','failed'])
        browser.assert_not_called();editor.assert_not_called();history.assert_not_called();native.assert_desktop.assert_not_called()

    def test_invoice_actions_cannot_run_through_gui_agent_worker(self):
        messages,browser,editor,history,native,worker=self.serve([
            {'requestId':'gui-invoice','kind':'show_invoice_demo','url':'http://127.0.0.1:8000/invoice-demo'},
            {'requestId':'gui-tests','kind':'run_invoice_tests','runId':'a'*32}],gui=True)
        self.assertEqual([m['status'] for m in messages if m['type']=='result'],['failed','failed'])
        browser.assert_not_called();editor.assert_not_called();history.assert_not_called();worker.run_agent.assert_not_called()
