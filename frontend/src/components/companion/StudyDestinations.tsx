import { useState } from 'react';

type Submit=(tool:string,args:Record<string,unknown>)=>void;

export function NotebookLMControls({pending,videoUrl,submit}:{pending:boolean;videoUrl:string;submit:Submit}) {
  const [isNew,setIsNew]=useState(true);
  const [notebook,setNotebook]=useState('');
  return <details className="aira-youtube-controls"><summary>NotebookLM → mind map</summary>
    <label>Notebook<select value={isNew?'new':'existing'} onChange={e=>setIsNew(e.target.value==='new')}>
      <option value="new">Create a new notebook</option><option value="existing">Use an existing notebook</option>
    </select></label>
    {!isNew && <label>Notebook link<input value={notebook} maxLength={1000} onChange={e=>setNotebook(e.target.value)} placeholder="Optional · otherwise use the one notebook open in AIRA Chrome" /></label>}
    <button disabled={pending} onClick={()=>submit('notebooklm_mindmap',{new_notebook:isNew,...(!isNew && notebook.trim()?{notebook_url:notebook.trim()}:{}),...(videoUrl.trim()?{video_url:videoUrl.trim()}: {})})}>Add video & generate mind map</button>
    <p>Uses your Google sign-in in AIRA Chrome. Imports the public video's captions into NotebookLM. Progress and the notebook link appear in Tasks. With no video link, it reads the selected AIRA YouTube tab.</p>
  </details>;
}

export function StudyDestinations({pending,studyTaskId,videoUrl,title,submit}:{pending:boolean;studyTaskId:string;videoUrl:string;title:string;submit:Submit}) {
  const [destination,setDestination]=useState('new');
  const [noteTitle,setNoteTitle]=useState(title.slice(0,160));
  const [page,setPage]=useState('');
  return <div>
    <details open className="aira-youtube-controls"><summary>Save the complete summary to Notion</summary>
      <label>Destination<select value={destination} onChange={e=>setDestination(e.target.value)}>
        <option value="new">Create a new page</option><option value="existing">Append to an existing page</option>
      </select></label>
      {destination==='new'?<label>New page title<input value={noteTitle} maxLength={160} onChange={e=>setNoteTitle(e.target.value)} /></label>:
        <label>Exact existing page title<input value={page} maxLength={160} onChange={e=>setPage(e.target.value)} placeholder="Leave empty to append to the selected Notion page" /></label>}
      <button disabled={pending || !studyTaskId || (destination==='new' && !noteTitle.trim())} onClick={()=>submit('export_summary_to_notion',{study_task_id:studyTaskId,destination,...(destination==='new'?{title:noteTitle.trim()}:{page_name:page.trim()})})}>Export saved summary</button>
      <p>Includes the source link, all points and caveats as text paragraphs. Existing content is preserved. Open the intended Notion workspace/page first; private, workspace and shared pages need edit access. A failed export may leave partial text: inspect it before retrying.</p>
    </details>
    <NotebookLMControls pending={pending} videoUrl={videoUrl} submit={submit} />
  </div>;
}
