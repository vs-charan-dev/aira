import { Link } from 'react-router-dom';

export function HowItWorksPage() {
  return <main className="min-h-screen bg-bg text-text-primary p-8 flex justify-center">
    <article className="max-w-2xl flex flex-col gap-6 py-12">
      <Link to="/" className="text-indigo-500">← AIRA</Link>
      <h1 className="text-4xl font-heading">Your Memory Palace</h1>
      <p>Open a local session, then add your Google AI Studio Gemini key in Settings. You can start with voice, screen sharing, or a webcam capture session.</p>
      <h2 className="text-2xl font-semibold">Capture and remember</h2>
      <p>Gemini listens to the input you enable and extracts concepts into topic rooms. Ask it to save a memory or a screenshot. Saved memories, embeddings, room layouts, and media are stored locally.</p>
      <h2 className="text-2xl font-semibold">Return and recall</h2>
      <p>Explore rooms, select an artifact, or talk to AIRA. Recall uses your saved memories as context; generated answers can still be mistaken. Generated diagrams and room synthesis require access and quota for the configured image model.</p>
      <h2 className="text-2xl font-semibold">Control your session</h2>
      <p>Allow the microphone, camera, or screen only when you want to use them. The current baseline switches between capture and recall. Stop capture to stop sending its live input. Closing AIRA stops the local backend.</p>
      <Link to="/palace" className="self-start px-6 py-3 rounded-xl bg-indigo-600 text-white">Open Memory Palace</Link>
    </article>
  </main>;
}
