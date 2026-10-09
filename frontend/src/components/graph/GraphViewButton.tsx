import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ArrowLeft, Network } from 'lucide-react';
import graphDocument from './memory-graph.html?raw';
import './graphView.css';

/** Presentation-only graph, bundled into the app without application data access. */
export function GraphViewButton() {
  const [open, setOpen] = useState(false);
  return <>
    <button type="button" className="aira-graph-button" onClick={() => setOpen(true)} aria-haspopup="dialog">
      <Network size={16} aria-hidden="true" /> Graph view
    </button>
    {open && <GraphView onClose={() => setOpen(false)} />}
  </>;
}

function GraphView({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal();
  }, []);

  return createPortal(
    <dialog ref={dialog} className="aira-graph-dialog" aria-labelledby="aira-graph-title" onCancel={onClose} onClose={onClose}>
      <header className="aira-graph-header">
        <div className="aira-graph-heading"><span>AIRA</span><span className="aira-graph-divider" /><Network size={17} aria-hidden="true" /><h2 id="aira-graph-title">Graph view</h2></div>
        <button autoFocus type="button" className="aira-graph-return" onClick={onClose}><ArrowLeft size={15} aria-hidden="true" /> Back to palace</button>
      </header>
      <iframe className="aira-graph-frame" title="AIRA memory graph" srcDoc={graphDocument} sandbox="allow-scripts" referrerPolicy="no-referrer" />
    </dialog>, document.body,
  );
}
