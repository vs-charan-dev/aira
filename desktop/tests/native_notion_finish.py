"""Explicit manual diagnostic: finish only the known blank test page ID.

Never invoked by unittest discovery, Electron, Gemini or the frontend. Supply
the ID recorded immediately after an approved native creation test. Stops if
the current private page differs or contains any text; does not create pages.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import windows_control as api
from notion_control import NotionController

if len(sys.argv) != 2 or len(sys.argv[1]) != 32 or any(c not in '0123456789abcdef' for c in sys.argv[1]):
    raise SystemExit('Supply the exact known test-page ID.')
api.user32.SetProcessDPIAware()
controller=NotionController(api)
controller.handle=api.foreground()
controller.created=True
try:
    message=controller.finish(sys.argv[1], 'AIRA verified demo 2026-10-08', 'Prepare the Memory Palace demo.\nCheck desktop voice controls.', resume_title=True)
    api.emit(type='result',status='succeeded',message=message)
except api.ActionError as error:
    api.emit(type='result',status='failed',message=str(error)); sys.exit(1)
except Exception as error:
    import traceback
    for frame in traceback.extract_tb(error.__traceback__)[-5:]:
        print(Path(frame.filename).name+':'+str(frame.lineno)+' '+frame.name,file=sys.stderr)
    print(type(error).__name__,file=sys.stderr)
    api.emit(type='result',status='failed',message='Diagnostic stopped. Inspect the partial test note before retrying.'); sys.exit(1)
