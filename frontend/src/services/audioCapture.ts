/**
 * AudioStreamer — streams raw PCM Int16 audio at 16kHz via AudioWorklet.
 *
 * Replaces the old MediaRecorder-based AudioCapture. Instead of recording
 * WebM chunks, this captures raw PCM suitable for Gemini Live's
 * send_realtime_input (audio/pcm;rate=16000).
 *
 * Each ~100ms, the worklet posts a 1600-sample Int16 buffer which is
 * base64-encoded and delivered to the callback.
 */

export class AudioStreamer {
    private ctx: AudioContext | null = null;
    private worklet: AudioWorkletNode | null = null;
    private stream: MediaStream | null = null;
    private _isStreaming = false;
    private generation = 0;
    private sink: GainNode | null = null;
    private watchdog: ReturnType<typeof setInterval> | null = null;

    /**
     * Start capturing microphone audio and streaming PCM chunks.
     * @param onPcmChunk Called every ~100ms with a base64-encoded Int16 PCM buffer.
     * @param additionalStream Optional extra MediaStream to mix in (e.g. display audio from screen share).
     */
    async start(onPcmChunk: (base64: string) => void, additionalStream?: MediaStream, onError?: (error: Error) => void): Promise<void> {
        const generation = ++this.generation;
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
            },
            video: false,
        });
        if (generation !== this.generation) {
            stream.getTracks().forEach(t => t.stop());
            return;
        }
        this.stream = stream;
        stream.getAudioTracks().forEach(track => track.addEventListener('ended', () => {
            if (generation === this.generation) onError?.(new Error('Microphone disconnected.'));
        }, { once: true }));

        // Create AudioContext at 16kHz — the browser will resample all inputs
        this.ctx = new AudioContext({ sampleRate: 16000 });
        if (this.ctx.state === 'suspended') await this.ctx.resume();
        if (generation !== this.generation || !this.ctx) return;

        // Load and register the PCM worklet processor
        await this.ctx.audioWorklet.addModule('/pcm-processor.js');
        if (generation !== this.generation || !this.ctx) return;
        this.worklet = new AudioWorkletNode(this.ctx, 'pcm-processor');
        this.worklet.onprocessorerror = () => {
            if (generation === this.generation) onError?.(new Error('Microphone processing stopped.'));
        };

        let lastChunk=Date.now();
        this.worklet.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
            if (generation !== this.generation || !this._isStreaming) return;
            lastChunk = Date.now();
            const pcmBytes = new Uint8Array(event.data);
            const base64 = uint8ToBase64(pcmBytes);
            onPcmChunk(base64);
        };

        // Connect microphone
        const micSource = this.ctx.createMediaStreamSource(this.stream);
        micSource.connect(this.worklet);
        // Keep a pulled audio graph when the Palace is behind another app.
        // The sink is silent: microphone audio is never played to the speakers.
        this.sink=this.ctx.createGain();this.sink.gain.value=0;
        this.worklet.connect(this.sink);this.sink.connect(this.ctx.destination);

        // Mix in display/screen-share audio if provided (e.g. YouTube tab audio)
        if (additionalStream) {
            const audioTracks = additionalStream.getAudioTracks();
            if (audioTracks.length > 0) {
                const displayAudioStream = new MediaStream(audioTracks);
                const displaySource = this.ctx.createMediaStreamSource(displayAudioStream);
                displaySource.connect(this.worklet);
            }
        }

        this._isStreaming = true;
        this.watchdog=setInterval(() => {
            if(generation===this.generation && this._isStreaming && Date.now()-lastChunk>6000) {
                if(this.watchdog) clearInterval(this.watchdog);
                this.watchdog=null;
                onError?.(new Error('Microphone stream paused. Activate AIRA again to reconnect.'));
            }
        },2000);
    }

    /** Stop capturing and release all resources. */
    stop(): void {
        this.generation++;
        this._isStreaming = false;
        if(this.watchdog) clearInterval(this.watchdog);
        this.watchdog=null;
        this.sink?.disconnect();this.sink=null;
        this.worklet?.disconnect();
        this.worklet = null;
        this.stream?.getTracks().forEach((t) => t.stop());
        this.stream = null;
        this.ctx?.close();
        this.ctx = null;
    }

    get isStreaming(): boolean {
        return this._isStreaming;
    }
}

/** Efficiently convert Uint8Array to base64. */
function uint8ToBase64(bytes: Uint8Array): string {
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

// Keep backward-compatible export name
export { AudioStreamer as AudioCapture };
