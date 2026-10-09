import { useEffect, useState } from 'react';
import { NotebookLMControls, StudyDestinations } from './StudyDestinations';

export type VideoModels = { summaryModel: string; imageModel: string };
type Props = { pending: boolean; models?:VideoModels; url:string; onUrl:(url:string)=>void;
  submit:(tool:string,args:Record<string,unknown>)=>void; saveModels:(models:VideoModels)=>void };

export function YouTubeControls({pending,models,url,onUrl,submit,saveModels}:Props) {
  const [query,setQuery]=useState('How an atom looks inside');
  const [output,setOutput]=useState('summary');
  const [selected,setSelected]=useState<VideoModels>({summaryModel:'gemini-3.5-flash-lite',imageModel:'gemini-3-pro-image'});
  useEffect(()=>{ if(models) setSelected(models); },[models?.summaryModel,models?.imageModel]);
  return <details open className="aira-youtube-controls"><summary>YouTube → learn & create</summary>
    <button disabled={pending} onClick={()=>submit('open_browser',{})}>Open AIRA Chrome</button>
    <label>Find a video<input value={query} maxLength={250} onChange={e=>setQuery(e.target.value)} /></label>
    <button disabled={pending || !query.trim()} onClick={()=>submit('search_youtube',{query})}>Search YouTube</button>
    <label>Video link<input value={url} onChange={e=>onUrl(e.target.value)} maxLength={1000} placeholder="Paste a link or leave empty for the active AIRA Chrome tab" /></label>
    <button disabled={pending || !url.trim()} onClick={()=>submit('open_youtube_video',{video_url:url})}>Open video</button>
    <label>Create<select value={output} onChange={e=>setOutput(e.target.value)}>
      <option value="transcript">Transcript · no Gemini generation</option><option value="summary">Summary</option>
      <option value="infographic">Infographic</option><option value="both">Summary & infographic</option>
    </select></label>
    <button disabled={pending || !url.trim()} onClick={()=>submit('youtube_study',{output,video_url:url.trim()})}>Create from video</button>
    <p>Select a search result or paste a link for these buttons. Voice can use the foreground YouTube tab in AIRA Chrome.</p>
    <p>Captions and files stay on E:. Summary/infographic generation sends caption content to Gemini using your saved key. Open a saved summary result to export it to Notion.</p>
    <NotebookLMControls pending={pending} videoUrl={url} submit={submit} />
    <details><summary>Generation models</summary>
      <label>Summary<select value={selected.summaryModel} onChange={e=>setSelected({...selected,summaryModel:e.target.value})}>
        <option value="gemini-3.5-flash-lite">Gemini 3.5 Flash-Lite</option><option value="gemini-2.5-flash-lite">Gemini 2.5 Flash-Lite</option><option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
      </select></label>
      <label>Infographic<select value={selected.imageModel} onChange={e=>setSelected({...selected,imageModel:e.target.value})}>
        <option value="gemini-3-pro-image">Nano Banana Pro · Gemini 3 Pro Image</option><option value="gemini-3.1-flash-image">Nano Banana 2 · Gemini 3.1 Flash Image</option><option value="gemini-2.5-flash-image">Gemini 2.5 Flash Image</option>
      </select></label>
      <button disabled={pending} onClick={()=>saveModels(selected)}>Save video models</button>
      <p>Applies to new requests. Access and billing depend on your key; no automatic paid retry or fallback.</p>
    </details>
  </details>;
}

export type StudyReport={kind:'youtube';studyTaskId:string;sourceUrl:string;summary:string;videoTitle:string;points?:{text:string;seconds:number}[];
  caveats?:string[];language?:string;autoCaptions?:boolean;assets:Record<string,string>;models:VideoModels};

export function VideoStudyResult({report,close,openSource,pending,submit}:{report:StudyReport;close:()=>void;openSource:(url:string)=>void;pending:boolean;submit:(tool:string,args:Record<string,unknown>)=>void}) {
  return <aside className="aira-job-report" aria-label="YouTube study result"><button onClick={close}>Close result</button>
    <h3>{report.videoTitle || 'Video study'}</h3><p>{report.summary}</p>
    <button onClick={()=>openSource(report.sourceUrl)}>Open source video in AIRA Chrome</button>
    {report.assets.summary && <StudyDestinations key={report.studyTaskId} pending={pending} studyTaskId={report.studyTaskId} videoUrl={report.sourceUrl} title={report.videoTitle} submit={submit} />}
    <p>{report.language || ''}{report.autoCaptions?' · automatic captions':''}. Based on captions; visual content and factual accuracy are not independently verified.</p>
    {report.points?.map((point,index)=><p key={index}><strong>{Math.floor(point.seconds/60)}:{String(point.seconds%60).padStart(2,'0')}</strong> · {point.text}</p>)}
    {report.caveats?.map((caveat,index)=><p key={index}>{caveat}</p>)}
    {report.assets.infographic && <img className="aira-infographic-preview" src={report.assets.infographic} alt="Generated infographic" />}
    {Object.entries(report.assets).map(([label,url])=><a key={label} href={url} download className="aira-study-download">Download {label.replace(/([A-Z])/g,' $1').toLowerCase()}</a>)}
    <small>{report.models.summaryModel} · {report.models.imageModel}</small>
  </aside>;
}
