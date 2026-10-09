import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight, BookOpen, Check, ChevronRight, Clock3, Search, ShieldCheck, Sparkles, X } from 'lucide-react';
import { personalMemoryApi, type PersonalMemory, type MemoryAnswer, type MemoryRoom, type MemoryStatus, type MemoryKind } from '../services/personalMemoryApi';
import './personalMemory.css';
import { GraphViewButton } from '../components/graph/GraphViewButton';

const EXAMPLES = ['What package am I targeting?', 'What did I learn from previous hackathons?', 'Why do I prefer simple architectures?', 'How should you explain technical topics to me?'];
const ROOM_SLOTS = [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 17, 19];

export function PersonalMemoryPage() {
  const [params, setParams] = useSearchParams();
  const [rooms, setRooms] = useState<MemoryRoom[]>([]);
  const [memories, setMemories] = useState<PersonalMemory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<MemoryAnswer | null>(null);
  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selected, setSelected] = useState<PersonalMemory | null>(null);
  const requestVersion = useRef(0);
  const roomId = params.get('room');
  const selectedRoom = rooms.find(r => r.id === roomId);
  const activeCount = memories.filter(m => m.status === 'active').length;

  useEffect(() => {
    let alive = true;
    personalMemoryApi.list().then(data => {
      if (alive) { setRooms(data.rooms); setMemories(data.memories); }
    }).catch(e => { if (alive) setError(e.message); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; requestVersion.current++; };
  }, []);

  useEffect(() => {
    const id = params.get('memory');
    if (id && memories.length) setSelected(memories.find(m => m.id === id) ?? null);
  }, [params, memories]);

  async function ask(value: string) {
    if (!value.trim()) return;
    const version = ++requestVersion.current;
    setQuery(value); setAsking(true); setError(''); setAnswer(null);
    try {
      const result = await personalMemoryApi.ask(value);
      if (requestVersion.current === version) setAnswer(result);
    } catch (e) { if (requestVersion.current === version) setError(e instanceof Error ? e.message : 'Could not search memories.'); }
    finally { if (requestVersion.current === version) setAsking(false); }
  }

  function closeDetail() {
    setSelected(null);
    if (params.has('memory')) { const next = new URLSearchParams(params); next.delete('memory'); setParams(next, { replace: true }); }
  }

  const visible = memories.filter(m => (!roomId || m.room_id === roomId) &&
    (statusFilter === 'all' || m.status === statusFilter) &&
    `${m.title} ${m.memory} ${m.id} ${m.tags.join(' ')}`.toLowerCase().includes(filter.toLowerCase()));

  return <main className="mp-page">
    <header className="mp-header">
      <Link to="/palace" className="mp-brand"><span className="mp-brand-icon">A</span><span>AIRA <small>PERSONAL CONTEXT</small></span></Link>
      <div className="aira-memory-header-actions"><GraphViewButton /><Link className="mp-back-link" to="/palace"><ArrowLeft size={15} /> Explore in 3D</Link></div>
    </header>
    <div className="mp-content">
      <div className="mp-intro"><div><p className="mp-eyebrow">A place for everything you remember</p><h1>Memory Palace<span>.</span></h1><p>Your goals, people, lessons and preferences. Every memory has a room.</p></div>
        <div className="mp-count"><strong>{loading ? '—' : activeCount}</strong><span>active memories<br />across {rooms.length || 15} rooms</span></div>
      </div>

      <section className="mp-query" aria-label="Ask about stored memories">
        <form onSubmit={e => { e.preventDefault(); void ask(query); }}><Sparkles size={21} /><input aria-label="Ask AIRA about me" placeholder="Ask AIRA about me..." value={query} onChange={e => setQuery(e.target.value)} maxLength={1000} /><button disabled={asking || !query.trim()} type="submit">{asking ? 'Searching…' : 'Ask AIRA'}<ArrowUpRight size={16} /></button></form>
        <div className="mp-examples">{EXAMPLES.map(example => <button key={example} onClick={() => void ask(example)} disabled={asking}>{example}</button>)}</div>
      </section>
      {error && <p className="mp-error" role="alert">{error}</p>}
      {answer && <section className="mp-answer" aria-live="polite"><div className="mp-answer-heading"><span><Sparkles size={17} /> AIRA’s memory answer <b className={`mp-kind mp-kind-${answer.kind}`}>{answer.kind}</b></span><button aria-label="Dismiss answer" onClick={() => setAnswer(null)}><X size={18} /></button></div>
        <p className="mp-answer-text">{answer.answer}</p>
        {answer.conflicts.length > 0 && <p className="mp-conflict">Conflicting references: {answer.conflicts.map(c => c.memory_ids.join(' / ')).join(', ')}</p>}
        {answer.references.length > 0 && <><p className="mp-eyebrow">Exact memories used</p><div className="mp-references">{answer.references.map(memory => <button onClick={() => setSelected(memories.find(m => m.id === memory.id) ?? memory)} key={memory.id}>{memory.room} <ChevronRight size={12} /><code>{memory.id}</code></button>)}</div></>}
        <small>Answers quote relevant stored memories. Plans are recorded as of October 9, 2026; exact event dates stay unknown until added.</small>
      </section>}

      {!roomId && <section aria-label="Palace room map" className="mp-map-section"><div className="mp-section-heading"><h2>Your palace</h2><span>Choose a room to enter <ChevronRight size={13} /></span></div>
        <div className="mp-palace-map"><div className="mp-hub"><div className="mp-hub-rings"><BookOpen size={33} /></div><strong>The central lobby</strong><span>15 rooms. One personal story.</span><button onClick={() => document.getElementById('mp-memory-list')?.scrollIntoView({ behavior: 'smooth' })}>Browse all memories <ArrowUpRight size={12} /></button></div>
          {rooms.map((room, i) => { const slot = ROOM_SLOTS[i]; const count = memories.filter(m => m.room_id === room.id).length; return <button className={`mp-room mp-room-${i % 5}`} style={{ gridColumn: (slot - 1) % 5 + 1, gridRow: Math.floor((slot - 1) / 5) + 1 }} key={room.id} onClick={() => { setParams({ room: room.id }); setFilter(''); }}><span className="mp-room-number">{String(i + 1).padStart(2, '0')}</span><span className="mp-room-icon">{room.icon}</span><strong>{room.name}</strong><span className="mp-room-meta">{count} memories <ArrowUpRight size={13} /></span></button>; })}
        </div>
      </section>}

      <section id="mp-memory-list" className="mp-library">
        <div className="mp-section-heading"><div>{selectedRoom && <button className="mp-return" onClick={() => setParams({})}><ArrowLeft size={14} /> All rooms</button>}<h2>{selectedRoom ? `${selectedRoom.icon} ${selectedRoom.name}` : 'All memories'}<span className="mp-total">{visible.length}</span></h2></div>{selectedRoom && <Link to={`/palace?room=${encodeURIComponent(selectedRoom.id)}`} className="mp-back-link">Enter this room in 3D <ArrowUpRight size={14} /></Link>}</div>
        <div className="mp-filters"><label><Search size={16} /><input placeholder="Filter cards by title, tag or memory ID" aria-label="Filter memory cards" value={filter} onChange={e => setFilter(e.target.value)} /></label><select aria-label="Filter by memory status" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option value="all">All statuses</option>{['active', 'outdated', 'uncertain', 'superseded'].map(s => <option key={s}>{s}</option>)}</select></div>
        {loading ? <p role="status">Opening your memory rooms…</p> : !visible.length ? <p className="mp-empty">No memories match this view.</p> : <div className="mp-cards">{visible.map(memory => <button key={memory.id} className={`mp-card mp-card-${memory.status}`} onClick={() => setSelected(memory)}><div className="mp-card-top"><code>{memory.id}</code><span className={`mp-kind mp-kind-${memory.kind}`}>{memory.kind}</span></div><h3>{memory.title}</h3><p>{memory.memory}</p><div className="mp-tags">{memory.tags.slice(0, 4).map(tag => <span key={tag}>{tag}</span>)}</div><div className="mp-card-footer"><span>{memory.importance} importance · {memory.status}</span><ArrowUpRight size={15} /></div></button>)}</div>}
      </section>
      <footer className="mp-footer"><ShieldCheck size={15} /> Stored personal context · Every answer is traceable · Corrections keep their history</footer>
    </div>
    {selected && <MemoryDetail key={`${selected.id}-${selected.version}`} memory={selected} memories={memories} onClose={closeDetail} onSelect={setSelected} onSave={updated => {
      setMemories(prev => prev.map(m => m.id === updated.id ? updated : m)); setSelected(updated); setAnswer(null);
    }} />}
  </main>;
}

function MemoryDetail({ memory, memories, onClose, onSave, onSelect }: { memory: PersonalMemory; memories: PersonalMemory[]; onClose: () => void; onSave: (memory: PersonalMemory) => void; onSelect: (memory: PersonalMemory) => void }) {
  const [text, setText] = useState(memory.memory);
  const [status, setStatus] = useState<MemoryStatus>(memory.status);
  const [kind, setKind] = useState<MemoryKind>(memory.kind);
  const [date, setDate] = useState(memory.event_date ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const dialogRef = useRef<HTMLDialogElement>(null);
  const related = memories.filter(m => m.id !== memory.id && (m.semantic_key === memory.semantic_key || m.tags.some(t => t !== m.category && memory.tags.includes(t)))).slice(0, 8);
  useEffect(() => { dialogRef.current?.showModal(); }, []);
  async function save() {
    setSaving(true); setError('');
    try { const result = await personalMemoryApi.correct(memory.id, { expected_version: memory.version, memory: text, status, kind, event_date: date || null }); onSave(result.memory); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not save correction.'); }
    finally { setSaving(false); }
  }
  return <dialog ref={dialogRef} className="mp-detail" aria-labelledby="mp-detail-title" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
    <div className="mp-detail-header"><span className="mp-eyebrow">{memory.room} / <code>{memory.id}</code></span><button onClick={onClose} aria-label="Close memory detail"><X size={21} /></button></div>
    <h2 id="mp-detail-title">{memory.title}</h2><div className="mp-detail-meta"><span className={`mp-kind mp-kind-${memory.kind}`}>{memory.kind}</span><span>{memory.importance} importance</span><span>Version {memory.version}</span></div>
    <label className="mp-field">Full memory<textarea aria-label="Full memory" value={text} onChange={e => setText(e.target.value)} rows={5} maxLength={4000} /></label>
    <div className="mp-detail-fields"><label className="mp-field">Status<select aria-label="Status" value={status} onChange={e => setStatus(e.target.value as MemoryStatus)}>{['active','outdated','uncertain','superseded'].map(s => <option key={s}>{s}</option>)}</select></label><label className="mp-field">Statement type<select aria-label="Statement type" value={kind} onChange={e => setKind(e.target.value as MemoryKind)}>{['fact','inference','unknown'].map(s => <option key={s}>{s}</option>)}</select></label><label className="mp-field">Event date<input aria-label="Event date" type="date" value={date} onChange={e => setDate(e.target.value)} /></label></div>
    <p className="mp-date-note"><Clock3 size={13} /> Created {memory.created_at} · Context as of {memory.as_of} · {memory.event_date ? `Event: ${memory.event_date}` : 'Event date unknown'}</p>
    <div className="mp-tags">{memory.tags.map(tag => <span key={tag}>{tag}</span>)}</div>
    <div className="mp-source"><strong>{memory.source}</strong><code>{memory.source_file}:{memory.source_line}</code><p>{memory.question}</p></div>
    {error && <p className="mp-error" role="alert">{error}</p>}<button className="mp-save" onClick={() => void save()} disabled={saving || !text.trim()}><Check size={16} />{saving ? 'Saving…' : 'Save correction'}</button>
    {related.length > 0 && <section className="mp-detail-related"><h3>Related memories</h3>{related.map(m => <button onClick={() => onSelect(m)} key={m.id}><code>{m.id}</code> {m.title}<ChevronRight size={13} /></button>)}</section>}
    <details className="mp-history"><summary>Revision history ({memory.history.length})</summary>{memory.history.length ? memory.history.slice().reverse().map(old => <article key={old.version}><strong>Version {old.version} · {old.status} · {old.kind}</strong><p>{old.memory}</p><small>{old.updated_at ?? old.created_at} · Event date: {old.event_date ?? 'unknown'}</small></article>) : <p>No corrections yet. The original version is kept when you save.</p>}</details>
  </dialog>;
}
