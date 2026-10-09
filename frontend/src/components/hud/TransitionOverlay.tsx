import { useTransitionStore } from '../../stores/transitionStore';

export function TransitionOverlay() {
    const isTransitioning = useTransitionStore(s => s.isTransitioning);
    return (
        <div
            className={`fixed inset-0 bg-[#060614] z-[9999] pointer-events-none transition-opacity duration-500 ease-in-out flex items-center justify-center ${isTransitioning ? 'opacity-100' : 'opacity-0'
                }`}
        >
            {/* Subtle glow or magical ring in the center */}
            <div className={`w-32 h-32 rounded-full border border-[rgba(255,255,255,0.1)] shadow-[0_0_80px_rgba(255,255,255,0.2)] transition-transform duration-1000 ${isTransitioning ? 'scale-150 opacity-100' : 'scale-50 opacity-0'
                }`} />
        </div>
    );
}
