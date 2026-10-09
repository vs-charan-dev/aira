import { useEffect, useRef, useState } from 'react';
import { AiraCharacter } from '../components/companion/AiraCharacter';
import type { CompanionState } from '../services/desktop';
import './desktopOverlay.css';
export function DesktopOverlayPage() {
  const energy = useRef(0);
  const [state, setState] = useState<CompanionState>({ mood: 'idle', label: 'Ready · Ctrl+Alt+A', busy: false, energy: 0, hiddenUntil: 0 });
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    document.documentElement.classList.add('aira-overlay-document');
    const desktop = window.airaDesktop;
    const unsubscribe = desktop?.onState(next => { energy.current = next.energy; setState(previous => previous.mood === next.mood && previous.label === next.label && previous.hiddenUntil === next.hiddenUntil ? previous : next); });
    desktop?.ready();
    return () => { unsubscribe?.(); document.documentElement.classList.remove('aira-overlay-document'); };
  }, []);
  useEffect(() => {
    setHidden(state.hiddenUntil > Date.now());
    const timer = setTimeout(() => setHidden(false), Math.max(0, state.hiddenUntil - Date.now()));
    return () => clearTimeout(timer);
  }, [state.hiddenUntil]);
  return <div className={`aira-native-face ${hidden ? 'aira-native-face--hidden' : ''}`}>
    <div className="aira-native-status" role="status">{state.label}</div>
    <AiraCharacter mood={state.mood} outputEnergy={energy} desktopGaze />
  </div>;
}
