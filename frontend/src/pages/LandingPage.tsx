import { Link } from 'react-router-dom';
import { Logo } from '../components/brand/Logo';

export function LandingPage() {
  return <main className="min-h-screen flex items-center justify-center bg-bg text-text-primary p-8">
    <div className="max-w-2xl text-center flex flex-col items-center gap-6">
      <Logo size={80} />
      <p className="text-indigo-500 tracking-widest uppercase font-semibold">AI AIRA</p>
      <h1 className="text-5xl font-heading">Your Memory Palace</h1>
      <p className="text-lg text-text-muted">Talk, capture meaningful moments, and return to what you remember. Explore your memories in rooms built around their topics.</p>
      <Link to="/palace" className="px-7 py-4 rounded-2xl bg-indigo-600 text-white font-semibold">Open Memory Palace</Link>
      <Link to="/how-it-works" className="text-indigo-500">How AIRA works</Link>
      <p className="text-sm text-text-muted">Memories and saved media stay on this computer. Voice, visual understanding, and generated content use Gemini with your Google AI Studio key.</p>
    </div>
  </main>;
}
