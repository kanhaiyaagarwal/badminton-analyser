/**
 * AudioWorklet processor that converts Float32 audio to Int16 PCM
 * and posts it to the main thread for WebSocket streaming.
 */
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this._buffer = new Float32Array(0)
    this._chunkSize = 4096
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || !input[0]) return true

    const samples = input[0]

    // Accumulate samples until we hit chunk size
    const merged = new Float32Array(this._buffer.length + samples.length)
    merged.set(this._buffer)
    merged.set(samples, this._buffer.length)
    this._buffer = merged

    while (this._buffer.length >= this._chunkSize) {
      const chunk = this._buffer.slice(0, this._chunkSize)
      this._buffer = this._buffer.slice(this._chunkSize)

      // Convert Float32 [-1,1] → Int16 PCM
      const pcm16 = new Int16Array(chunk.length)
      for (let i = 0; i < chunk.length; i++) {
        pcm16[i] = Math.max(-32768, Math.min(32767, chunk[i] * 32768))
      }
      this.port.postMessage(pcm16.buffer, [pcm16.buffer])
    }

    return true
  }
}

registerProcessor('pcm-processor', PCMProcessor)
