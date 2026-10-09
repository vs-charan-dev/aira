// Read only AIRA output audio, never microphone input.
const meters = new Set<AnalyserNode>();
const samples = new WeakMap<AnalyserNode, Float32Array<ArrayBuffer>>();

export function registerPlaybackMeter(meter: AnalyserNode): () => void {
  meters.add(meter);
  samples.set(meter, new Float32Array(meter.fftSize));
  return () => { meters.delete(meter); samples.delete(meter); };
}

export function getPlaybackEnergy(): number {
  let loudest = 0;
  for (const meter of meters) {
    const data = samples.get(meter);
    if (!data) continue;
    meter.getFloatTimeDomainData(data);
    let sum = 0;
    for (const value of data) sum += value * value;
    loudest = Math.max(loudest, Math.sqrt(sum / data.length));
  }
  return Math.min(1, loudest * 7);
}
