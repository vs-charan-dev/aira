import { useEffect, useRef, useState } from 'react';
import { taskRequest } from './TaskBoard';

type Event = {at:number;text:string};
export function CodingLog({jobId, status}: {jobId:string;status:string}) {
  const [events,setEvents] = useState<Event[]>([]);
  const [error,setError] = useState('');
  const pane = useRef<HTMLPreElement>(null);
  const follow = useRef(true);
  useEffect(() => {
    let disposed=false;
    let timer:ReturnType<typeof setTimeout>;
    const controller=new AbortController();
    setEvents([]); setError('');
    const refresh=async()=>{
      try {
        const value=await taskRequest<{events:Event[]}>('/'+jobId+'/events',undefined,'GET',controller.signal);
        if(!disposed) {setEvents(value.events);setError('');}
      } catch(e) {if(!disposed) setError(e instanceof Error?e.message:'Command log unavailable.');}
      finally {if(!disposed && ['running','queued'].includes(status)) timer=setTimeout(()=>void refresh(),1000);}
    };
    void refresh();
    return ()=>{disposed=true;clearTimeout(timer);controller.abort();};
  },[jobId,status]);
  useEffect(()=>{if(pane.current && follow.current) pane.current.scrollTop=pane.current.scrollHeight;},[events]);
  return <div className="aira-coding-log">
    <div className="aira-coding-log-title"><span>Live command log</span><span>{status.replaceAll('_',' ')}</span></div>
    <pre ref={pane} aria-label="Observed coding commands and test output" onScroll={()=>{const el=pane.current;if(el) follow.current=el.scrollHeight-el.scrollTop-el.clientHeight<35;}}>{events.length?events.map((event,index)=><span key={index}><time>{new Date(event.at*1000).toLocaleTimeString()}</time> {event.text}{'\n'}</span>):'Waiting for worker output…'}</pre>
    {error && <p role="alert">{error}</p>}
  </div>;
}
