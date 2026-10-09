/**
 * AudioPlayback — streams base64-encoded PCM audio chunks over Web Audio API.
 *
 * Gemini Live API returns raw Linear16 PCM (24 kHz, mono, 16-bit).
 * The browser's decodeAudioData() cannot handle raw PCM — we must wrap it
 * in a WAV container first.
 *
 * Usage pattern:
 *   const player = new AudioPlayback();
 *   player.enqueue('base64data...');  // called per response_chunk
 *   player.stop();                    // on interrupt or end
 */

/** Sample rate Gemini Live uses for its audio output. */
import { registerPlaybackMeter } from './playbackMeter';
import { getAudioOutputState, onAudioRoutingChange, reportAudioOutputError } from './audioOutput';

const GEMINI_SAMPLE_RATE = 24000;
const activePlayers = new Set<AudioPlayback>();
let microphoneReleaseAt = 0;
/** Queue activity, including silent gaps, keeps the character's speaking state stable. */
export function isPlaybackActive(): boolean { return [...activePlayers].some(player => player.isPlaying); }
/** Allow speaker echoes to decay before resuming microphone transmission. */
export function isPlaybackBlockingInput(): boolean { return isPlaybackActive() || Date.now() < microphoneReleaseAt; }
export function stopAllPlayback(): void { for (const player of [...activePlayers]) player.stop(); }

/**
 * Wrap raw Linear16 PCM bytes in a minimal WAV container so the browser's
 * decodeAudioData() can parse them.
 */
function pcmToWav(pcmBytes: Uint8Array, sampleRate = GEMINI_SAMPLE_RATE): ArrayBuffer {
    const numChannels = 1;
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
    const blockAlign = numChannels * (bitsPerSample / 8);
    const dataSize = pcmBytes.byteLength;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);

    const write = (offset: number, val: string) =>
        [...val].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));

    write(0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    write(8, 'WAVE');
    write(12, 'fmt ');
    view.setUint32(16, 16, true);           // subchunk1 size
    view.setUint16(20, 1, true);            // PCM format
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    write(36, 'data');
    view.setUint32(40, dataSize, true);
    new Uint8Array(buffer, 44).set(pcmBytes);
    return buffer;
}

export class AudioPlayback {
    private ctx: AudioContext | null = null;
    private scheduledUntil = 0;
    private bufferQueue: AudioBufferSourceNode[] = [];
    private _isPlaying = false;
    private meter: AnalyserNode | null = null;
    private releaseMeter: (() => void) | null = null;
    private generation = 0;
    private releaseRouting: (() => void) | null = null;
    private outputReady: Promise<void> | null = null;
    private enqueueTail: Promise<void> = Promise.resolve();
    private pendingChunks = 0;

    private getContext(): AudioContext {
        activePlayers.add(this);
        if (!this.ctx || this.ctx.state === 'closed') {
            this.releaseMeter?.();
            this.releaseRouting?.();
            this.meter?.disconnect();
            // Let Windows choose the hardware rate. Decoded PCM still carries
            // Gemini's 24 kHz rate and Web Audio resamples it for the speakers.
            this.ctx = new AudioContext();
            this.meter = this.ctx.createAnalyser();
            this.meter.fftSize = 256;
            this.meter.connect(this.ctx.destination);
            this.releaseMeter = registerPlaybackMeter(this.meter);
            this.releaseRouting = onAudioRoutingChange(() => this.stop());
            const ctx = this.ctx as AudioContext & { setSinkId?: (id: string) => Promise<void> };
            const deviceId = getAudioOutputState().deviceId;
            this.outputReady = deviceId
                ? (ctx.setSinkId ? ctx.setSinkId(deviceId) : Promise.reject(new Error('This browser cannot select a speaker. Use Windows default output.')))
                : Promise.resolve();
            // A failure is surfaced by activate/enqueue, without an unhandled rejection.
            void this.outputReady.catch(() => {});
            this.scheduledUntil = 0;
        }
        return this.ctx;
    }

    /** Call directly from a user gesture before loading an offline sample. */
    async activate(): Promise<void> {
        const generation = this.generation;
        const ctx = this.getContext();
        try {
            await this.outputReady;
            if (generation !== this.generation || ctx !== this.ctx) return;
            if (ctx.state !== 'running' && ctx.state !== 'closed') await ctx.resume();
        } catch (error) {
            if (generation === this.generation) reportAudioOutputError(error);
            throw error;
        }
    }

    /**
     * Decode and schedule a base64-encoded PCM audio chunk for playback.
     * Chunks are played sequentially without gaps.
     */
    enqueue(base64: string): Promise<void> {
        const generation = this.generation;
        activePlayers.add(this);
        this.pendingChunks++;
        // Web Audio decode/resume promises may complete out of arrival order.
        // Serialize the entire scheduling path, and detach it when stopped.
        const next = this.enqueueTail.then(async () => {
            if (generation !== this.generation) return;
            await this.scheduleChunk(base64, generation);
        }).finally(() => {
            if (generation === this.generation) this.pendingChunks--;
        });
        this.enqueueTail = next;
        return next;
    }

    private async scheduleChunk(base64: string, generation: number): Promise<void> {
        try {
            const binary = atob(base64);
            const pcmBytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                pcmBytes[i] = binary.charCodeAt(i);
            }

            // Wrap raw Linear16 PCM → WAV so decodeAudioData can parse it
            const wavBuffer = pcmToWav(pcmBytes);

            const ctx = this.getContext();
            await this.outputReady;
            if (generation !== this.generation || ctx !== this.ctx) return;
            const audioBuffer = await ctx.decodeAudioData(wavBuffer);
            // A stopped/replaced session must not schedule a late decoded chunk.
            if (generation !== this.generation || ctx !== this.ctx) return;
            if (ctx.state !== 'running' && ctx.state !== 'closed') await ctx.resume();
            if (generation !== this.generation || ctx !== this.ctx) return;

            const source = ctx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.meter!);

            // A small initial buffer absorbs ordinary arrival/decoding jitter.
            const startTime = Math.max(ctx.currentTime + (this.bufferQueue.length ? 0 : .08), this.scheduledUntil);
            source.start(startTime);
            this.scheduledUntil = startTime + audioBuffer.duration;

            source.onended = () => {
                const idx = this.bufferQueue.indexOf(source);
                if (idx !== -1) this.bufferQueue.splice(idx, 1);
                if (this.bufferQueue.length === 0 && generation === this.generation) {
                    this._isPlaying = false;
                    microphoneReleaseAt = Date.now() + 250;
                }
            };

            this.bufferQueue.push(source);
            this._isPlaying = true;
        } catch (err) {
            if (generation === this.generation) {
                reportAudioOutputError(err);
                console.error('[AudioPlayback] Failed to decode/schedule chunk:', err);
            }
        }
    }

    /**
     * Stop all currently scheduled/playing nodes immediately and close the
     * AudioContext so the browser releases hardware resources.
     */
    stop(): void {
        activePlayers.delete(this);
        this.generation += 1;
        this.enqueueTail = Promise.resolve();
        this.pendingChunks = 0;
        if (this._isPlaying) microphoneReleaseAt = Date.now() + 250;
        for (const node of this.bufferQueue) {
            try {
                node.stop();
            } catch {
                // Already stopped — safe to ignore
            }
        }
        this.bufferQueue = [];
        this.scheduledUntil = 0;
        this._isPlaying = false;
        this.releaseMeter?.();
        this.releaseMeter = null;
        this.releaseRouting?.();
        this.releaseRouting = null;
        this.outputReady = null;
        this.meter?.disconnect();
        this.meter = null;
        if (this.ctx && this.ctx.state !== 'closed') void this.ctx.close().catch(() => {});
        this.ctx = null;
    }

    get isPlaying(): boolean {
        return this._isPlaying || this.pendingChunks > 0;
    }
}
