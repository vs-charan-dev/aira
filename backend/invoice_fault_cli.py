"""Local rehearsal helpers; never needed by the voice repair implementation."""
import argparse
import asyncio
import sys
from app.services import invoice_demo as demo
from app.services.invoice_faults import create_fault, run_deterministic_repair, assert_not_busy


async def run(mode):
    async def progress(label): print(label, flush=True)
    if mode == 'create':
        info = create_fault()
        value = await demo.evaluate(200,10,info['version'])
        if value['total'] != 190: raise ValueError('The recreated faulty output could not be verified.')
        print('Fault created: 200 with 10% off displays 190. The localhost app refreshes automatically.')
    else:
        assert_not_busy()
        info = demo.prepare()
        result = await run_deterministic_repair({'id':None,'project':{'path':info['path'],'runner':'node'},'demoGeneration':info['generation']},progress)
        if not result['report']['verified']: raise ValueError(result['message'])
        value = await demo.evaluate(200,10,demo.version())
        if value['total'] != 180: raise ValueError('The corrected output could not be verified.')
        print('Fault fixed: 200 with 10% off displays 180. The localhost app refreshes automatically.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['create','fix']);args=parser.parse_args()
    try: asyncio.run(run(args.mode))
    except (ValueError,OSError) as error:
        print(str(error),file=sys.stderr);sys.exit(1)
