import { useEffect, useId, useRef } from 'react';
import { getPlaybackEnergy } from '../../services/playbackMeter';
import './character.css';

export type CharacterMood = 'idle' | 'listening' | 'thinking' | 'capturing' | 'speaking' | 'error';

// One ellipse owns the fill, clip, and full rim, so there are no joined contour segments.
const FACE_ELLIPSE = { cx: 240, cy: 270, rx: 244, ry: 210 };

/** Procedural vector character. Pointer coordinates can later come from the desktop/gesture host. */
export function AiraCharacter({ mood = 'idle', blinkSignal = 0, outputEnergy, desktopGaze = false }: { mood?: CharacterMood; blinkSignal?: number; outputEnergy?: { current: number }; desktopGaze?: boolean }) {
  const id = useId().replace(/:/g, '');
  const svg = useRef<SVGSVGElement>(null);
  const pupilLeft = useRef<SVGGElement>(null);
  const pupilRight = useRef<SVGGElement>(null);
  const eyeLeft = useRef<SVGGElement>(null);
  const eyeRight = useRef<SVGGElement>(null);
  const mouth = useRef<SVGEllipseElement>(null);
  const mouthClip = useRef<SVGEllipseElement>(null);
  const tongue = useRef<SVGGElement>(null);
  const blinkAt = useRef(-Infinity);
  const previousBlink = useRef(blinkSignal);
  const moodRef = useRef(mood);
  moodRef.current = mood;
  useEffect(() => {
    if (previousBlink.current !== blinkSignal) blinkAt.current = performance.now();
    previousBlink.current = blinkSignal;
  }, [blinkSignal]);
  useEffect(() => {
    let frame = 0;
    let pointer: { x: number; y: number; at: number } | null = null;
    let x = 0, y = 0, energy = 0, last = performance.now();
    let nextBlink = last + 2400 + Math.random() * 2600;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    const move = (event: PointerEvent) => { pointer = { x: event.clientX, y: event.clientY, at: performance.now() }; };
    let lastDesktopPoint = { x: NaN, y: NaN };
    const unsubscribeCursor = desktopGaze ? window.airaDesktop?.onCursor(point => {
      if (point.x === lastDesktopPoint.x && point.y === lastDesktopPoint.y) return;
      lastDesktopPoint = point;
      pointer = { ...point, at: performance.now() };
    }) : undefined;
    const leave = () => { pointer = null; };
    const tick = (now: number) => {
      const dt = Math.min(60, now - last); last = now;
      const currentMood = moodRef.current;
      const faceViewer = currentMood === 'speaking' || currentMood === 'listening' || currentMood === 'capturing';
      let tx = 0, ty = currentMood === 'thinking' ? -7 : 0;
      if (!faceViewer && pointer && now - pointer.at < 2400 && svg.current) {
        const box = svg.current.getBoundingClientRect();
        tx = (pointer.x - (box.left + box.width / 2)) / Math.max(box.width, 1) * 30;
        ty = (pointer.y - (box.top + box.height * .57)) / Math.max(box.height, 1) * 24;
        const distance = Math.hypot(tx / 15, ty / 12);
        if (distance > 1) { tx /= distance; ty /= distance; }
      }
      const smoothing = reduced.matches ? 1 : 1 - Math.exp(-dt / 90);
      x += (tx - x) * smoothing; y += (ty - y) * smoothing;
      pupilLeft.current?.setAttribute('transform', `translate(${x} ${y})`);
      pupilRight.current?.setAttribute('transform', `translate(${x} ${y})`);
      if (now >= nextBlink && !reduced.matches) {
        blinkAt.current = now;
        nextBlink = now + 3200 + Math.random() * 3500;
      }
      const elapsed = now - blinkAt.current;
      const closed = elapsed >= 0 && elapsed < 210 ? Math.sin(elapsed / 210 * Math.PI) : 0;
      const openness = Math.max(.035, 1 - closed);
      eyeLeft.current?.setAttribute('transform', `translate(0 ${155 * (1 - openness)}) scale(1 ${openness})`);
      eyeRight.current?.setAttribute('transform', `translate(0 ${155 * (1 - openness)}) scale(1 ${openness})`);
      const target = outputEnergy?.current ?? getPlaybackEnergy();
      energy += (target - energy) * (1 - Math.exp(-dt / (target > energy ? 35 : 75)));
      const mouthRx = 13.5 + energy * 8;
      const mouthRy = 7.8 + energy * 21;
      for (const ellipse of [mouth.current, mouthClip.current]) {
        ellipse?.setAttribute('rx', String(mouthRx));
        ellipse?.setAttribute('ry', String(mouthRy));
      }
      tongue.current?.setAttribute('transform', `translate(240 ${236 + mouthRy * .7}) scale(${mouthRx / 13.5} ${mouthRy / 7.8})`);
      frame = requestAnimationFrame(tick);
    };
    window.addEventListener('pointermove', move);
    document.documentElement.addEventListener('pointerleave', leave);
    window.addEventListener('blur', leave);
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('pointermove', move);
      document.documentElement.removeEventListener('pointerleave', leave);
      window.removeEventListener('blur', leave);
      unsubscribeCursor?.();
    };
  }, [outputEnergy, desktopGaze]);
  const eye = (cx: number, eyeRef: typeof eyeLeft, pupilRef: typeof pupilLeft) => (
    <g ref={eyeRef}>
      <defs><clipPath id={`${id}-eye-clip-${cx}`}><ellipse cx={cx} cy="155" rx="51" ry="59" /></clipPath></defs>
      <ellipse cx={cx} cy="155" rx="51" ry="59" fill={`url(#${id}-eye)`} />
      <ellipse cx={cx} cy="155" rx="51" ry="59" fill="none" stroke="#bcdeff" strokeWidth="1.5" />
      <g clipPath={`url(#${id}-eye-clip-${cx})`}>
        <g ref={pupilRef}>
          <ellipse cx={cx + 3} cy="146" rx="27" ry="31" fill={`url(#${id}-pupil)`} />
          <ellipse cx={cx - 7} cy="130" rx="10" ry="11" fill="white" opacity=".96" />
          <circle cx={cx + 15} cy="159" r="4.5" fill="#b9d5ff" opacity=".85" />
          <ellipse cx={cx + 1} cy="167" rx="11" ry="3" fill="#8193e8" opacity=".25" />
        </g>
      </g>
    </g>
  );
  return (
    <svg ref={svg} className={`aira-character aira-character--${mood}`} viewBox="0 0 480 270" role="img" aria-label={`AIRA character, ${mood}`}>
      <defs>
        <radialGradient id={`${id}-body`} cx="32%" cy="22%" r="86%">
          <stop stopColor="#96caff" /><stop offset=".37" stopColor="#508dff" /><stop offset=".77" stopColor="#3260ed" /><stop offset="1" stopColor="#2445bb" />
        </radialGradient>
        <linearGradient id={`${id}-eye`} x2=".3" y2="1"><stop stopColor="#fff" /><stop offset="1" stopColor="#d8efff" /></linearGradient>
        <radialGradient id={`${id}-pupil`} cx="40%" cy="25%"><stop stopColor="#303962" /><stop offset="1" stopColor="#131b39" /></radialGradient>
        <radialGradient id={`${id}-cheek`}><stop stopColor="#f6bcf2" stopOpacity=".6" /><stop offset="1" stopColor="#b49bfd" stopOpacity="0" /></radialGradient>
        <radialGradient id={`${id}-corner-glow`}>
          <stop stopColor="#b1d5ff" stopOpacity=".28" />
          <stop offset=".45" stopColor="#a4a9ff" stopOpacity=".13" />
          <stop offset="1" stopColor="#8d9bff" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${id}-rim-glow`} x1="0" y1="1" x2="1" y2="0">
          <stop stopColor="#18388f" stopOpacity=".65" />
          <stop offset=".35" stopColor="#345edc" stopOpacity=".8" />
          <stop offset=".65" stopColor="#2142b5" stopOpacity=".85" />
          <stop offset="1" stopColor="#142f94" stopOpacity=".65" />
        </linearGradient>
        <filter id={`${id}-rim-halo`} x="-40%" y="-50%" width="180%" height="200%"><feGaussianBlur stdDeviation="18" /></filter>
        <filter id={`${id}-rim-blur`} x="-40%" y="-50%" width="180%" height="200%"><feGaussianBlur stdDeviation="7" /></filter>
        <clipPath id={`${id}-face-clip`}><ellipse {...FACE_ELLIPSE} /></clipPath>
        <clipPath id={`${id}-mouth-clip`}><ellipse ref={mouthClip} cx="240" cy="236" rx="13.5" ry="7.8" /></clipPath>
        <linearGradient id={`${id}-tongue`} x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#ffb1c6" /><stop offset="1" stopColor="#df749b" />
        </linearGradient>
      </defs>
      <g className="aira-body">
        <ellipse {...FACE_ELLIPSE} fill="none" stroke={`url(#${id}-rim-glow)`} strokeWidth="36" opacity=".65" filter={`url(#${id}-rim-halo)`} />
        <ellipse {...FACE_ELLIPSE} fill="none" stroke={`url(#${id}-rim-glow)`} strokeWidth="18" opacity=".7" filter={`url(#${id}-rim-blur)`} />
        <ellipse {...FACE_ELLIPSE} fill={`url(#${id}-body)`} />
        <ellipse {...FACE_ELLIPSE} fill="none" stroke={`url(#${id}-rim-glow)`} strokeWidth="1.5" opacity=".3" />
        <g clipPath={`url(#${id}-face-clip)`}>
          <ellipse cx="67" cy="243" rx="70" ry="51" fill={`url(#${id}-corner-glow)`} />
          <ellipse cx="413" cy="243" rx="70" ry="51" fill={`url(#${id}-corner-glow)`} />
        </g>
        {/* The tuft straddles the crown: its lower points remain on the face. */}
        <path d="M239 61 C241 66 244 66 250 63 C247 68 247 72 251 76 C246 74 243 75 239 79 C239 74 235 71 230 71 C235 69 238 66 239 61Z" fill="#2b43ce" transform="translate(0 -9)" />
        <path d="M130 92 Q156 79 183 88" fill="none" stroke="#304fae" strokeWidth="8" strokeLinecap="round" opacity=".9" />
        <path d="M297 88 Q324 79 350 92" fill="none" stroke="#304fae" strokeWidth="8" strokeLinecap="round" opacity=".9" />
        {eye(160, eyeLeft, pupilLeft)}
        {eye(320, eyeRight, pupilRight)}
        <ellipse cx="105" cy="221" rx="34" ry="20" fill={`url(#${id}-cheek)`} />
        <ellipse cx="375" cy="221" rx="34" ry="20" fill={`url(#${id}-cheek)`} />
        <ellipse ref={mouth} cx="240" cy="236" rx="13.5" ry="7.8" fill="#192f8e" stroke="#3457cb" strokeWidth="2" />
        {mood === 'speaking' && (
          <g clipPath={`url(#${id}-mouth-clip)`}>
            <g ref={tongue} transform="translate(240 241.46)">
              <ellipse rx="8" ry="2.8" fill={`url(#${id}-tongue)`} />
              <path d="M0 -2.1 V-.5" fill="none" stroke="#d46f94" strokeWidth=".7" strokeLinecap="round" />
            </g>
          </g>
        )}
      </g>
    </svg>
  );
}
