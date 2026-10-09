"""Bounded, visible basic arithmetic in Windows Calculator; no model or eval."""
import re
from decimal import Decimal, localcontext


def expression(value):
    if not isinstance(value,str) or len(value)>80:
        raise ValueError('Provide two numbers with +, -, * or /.')
    text=value.replace('×','*').replace('÷','/').replace('−','-').strip()
    match=re.fullmatch(r'(\d{1,12}(?:\.\d{1,8})?)\s*([+*/-])\s*(\d{1,12}(?:\.\d{1,8})?)',text)
    if not match: raise ValueError('Direct Calculator supports two nonnegative numbers and +, -, * or /. Use a desktop task for another operation.')
    left,op,right=match.groups()
    with localcontext() as context:
        context.prec=28
        a,b=Decimal(left),Decimal(right)
        if op=='/' and b==0: raise ValueError('Division by zero is not supported.')
        result={'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:a/b}[op]()
    return left,op,right,result


def result_control(api,handle,include_offscreen=False):
    if api.process_name(handle) not in ('calculatorapp.exe','calculator.exe','applicationframehost.exe'):
        return None
    root=api.u.ControlFromHandle(handle)
    for ident in ('CalculatorResults','CalculatorAlwaysOnTopResults'):
        control=root.Control(searchDepth=15,AutomationId=ident)
        if control.Exists(.05) and (include_offscreen or not control.IsOffscreen): return control
    return None


def run(api,value):
    try: left,op,right,expected=expression(value)
    except ValueError as error: raise api.ActionError(str(error))
    if not result_control(api,api.foreground()): api.open_app('Calculator')
    handle=api.foreground()
    if not result_control(api,handle): raise api.ActionError('The Calculator result display could not be identified. No calculation was entered.')
    api.progress('Selecting Standard Calculator')
    api.chord(0x12,ord('1'))
    def button(ident):
        if api.foreground()!=handle: raise api.ActionError('Calculator lost focus. Calculation stopped.')
        control=api.u.ControlFromHandle(handle).ButtonControl(searchDepth=15,AutomationId=ident)
        return control if control.Exists(.05) and not control.IsOffscreen and control.IsEnabled else None
    clear=api.wait(lambda:button('clearButton'),3)
    if not clear: raise api.ActionError('Standard Calculator controls were not ready. No calculation was entered.')
    # Resolve all requested controls before clearing the previous result.
    identifiers=['clearButton']+[('decimalSeparatorButton' if c=='.' else 'num'+c+'Button') for c in left]
    identifiers.append({'+':'plusButton','-':'minusButton','*':'multiplyButton','/':'divideButton'}[op])
    identifiers += [('decimalSeparatorButton' if c=='.' else 'num'+c+'Button') for c in right]+['equalButton']
    controls={ident:button(ident) for ident in set(identifiers)}
    if not all(controls.values()): raise api.ActionError('Calculator did not expose the required buttons. No calculation was entered.')
    api.progress('Calculating '+left+' '+op+' '+right)
    for ident in identifiers: api.click(controls[ident],handle)
    def matches():
        if api.foreground()!=handle: raise api.ActionError('Calculator lost focus before result verification.')
        control=result_control(api,handle)
        if not control: return False
        numbers=re.findall(r'-?\d[\d,]*(?:\.\d+)?',control.Name.replace('\u2212','-'))
        if len(numbers)!=1: return False
        actual=Decimal(numbers[0].replace(',',''))
        return actual if abs(actual-expected)<=max(Decimal('1e-12'),abs(expected)*Decimal('1e-12')) else False
    # Zero is a legitimate result; wrap the predicate so wait does not treat it as false.
    verified=api.wait(lambda: (True,observed) if (observed:=matches()) is not False else None,3)
    if not verified: raise api.ActionError('Calculator result did not match the independently computed answer. Inspect the display before retrying.')
    answer=format(expected,'f')
    if '.' in answer: answer=answer.rstrip('0').rstrip('.')
    return left+' '+op+' '+right+' = '+answer
