"""Warm, sequential desktop worker. JSON-lines stdin/stdout; no input while idle.

Electron kills this owned process on cancellation and waits for exit before reuse.
Fresh agents are constructed per GUI task; only imported dependencies are retained.
"""
import contextlib
import json
import logging
import sys
import time

PROTOCOL = sys.stdout
PROTOCOL.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')
logging.disable(logging.CRITICAL)


def send(**message):
    print(json.dumps(message, ensure_ascii=False), file=PROTOCOL, flush=True)


def serve():
    gui = '--gui' in sys.argv
    if gui:
        import windows_use_worker as worker
        parts = worker.dependencies()
        native = parts[-1]
    else:
        import windows_control as native
        worker, parts = None, None
    # Cache only installed-app metadata, not screen trees or inferred actions.
    try: native.catalog()
    except Exception: pass
    from desktop_history import History
    native.user32.SetProcessDPIAware()
    send(type='ready')
    for line in sys.stdin:
        if len(line)>128000:
            return
        ident = None
        history = None
        began = time.monotonic()
        first_input = None
        try:
            value = json.loads(line)
            ident = value.get('requestId')
            if not isinstance(ident,str) or not 1<=len(ident)<=80 or not all(c.isalnum() or c=='-' for c in ident):
                raise ValueError('Invalid task ID')
            action = {k:v for k,v in value.items() if k != 'requestId'}
            if gui:
                from windows_use_policy import validate_action
                action = validate_action(action)
                if action['kind'] != 'desktop_task': raise ValueError('Unsupported GUI task')
            elif action.get('kind') not in ('export_summary_to_notion','notebooklm_mindmap','open_app','open_folder','close_app','type_in_app','calculate_in_app','show_project','show_invoice_demo','run_invoice_tests','create_notion_note','list_apps','open_browser','open_maps','search_maps','search_youtube','open_youtube_video','current_youtube_video'):
                raise ValueError('Unsupported action')
            if action['kind'] != 'list_apps': history = History(ident, action)
            native._input_started = False

            def emit(**message):
                nonlocal first_input
                if message.get('type')=='action_started' and first_input is None:
                    first_input = round((time.monotonic()-began)*1000)
                if message.get('type')=='result':
                    message['timings'] = {'executionMs':round((time.monotonic()-began)*1000), 'firstInputMs':first_input}
                    if history:
                        history.finish(message['status'],message['message'],timings=message['timings'])
                send(requestId=ident, **message)

            native.emit = emit
            if gui:
                worker.emit = emit
                native.assert_desktop()
                status, message, input_tokens, output_tokens = worker.run_agent(action,history,parts)
                history.finish(status,message,input_tokens,output_tokens)
                emit(type='result',status=status,message=message)
            else:
                native.execute(action)
        except Exception as error:
            from windows_control import ActionError
            known = isinstance(error, ActionError)
            if gui:
                from windows_use_policy import PolicyError
                known = known or isinstance(error, PolicyError)
            message = str(error)[:400] if known else 'Desktop worker could not complete this task. Inspect partial changes before retrying.'
            if history:
                try: history.finish('failed',message)
                except Exception: pass
            send(type='result',requestId=ident,status='failed',message=message,
                 data=getattr(error,'data',{}),
                 timings={'executionMs':round((time.monotonic()-began)*1000),'firstInputMs':first_input})


if __name__=='__main__':
    with contextlib.redirect_stdout(sys.stderr):
        try: serve()
        except Exception:
            send(type='unavailable')
            sys.exit(1)
