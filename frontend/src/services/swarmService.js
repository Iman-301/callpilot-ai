/**
 * Service for connecting to the swarm streaming API
 * Handles SSE parsing and event callbacks
 */

const parseSseEvents = (chunk) => {
  const normalized = chunk.replace(/\r\n/g, '\n');
  const events = [];
  const blocks = normalized.split('\n\n');
  for (const block of blocks) {
    if (!block.trim()) continue;
    const lines = block.split('\n');
    let eventType = 'message';
    let data = '';
    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventType = line.replace('event:', '').trim();
      } else if (line.startsWith('data:')) {
        data += line.replace('data:', '').trim();
      }
    }
    if (data) {
      events.push({ type: eventType, data });
    }
  }
  return events;
};

export const startSwarm = async (payload, callbacks) => {
  const { onStart, onProgress, onComplete, onError } = callbacks;

  try {
    const response = await fetch('/swarm/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const normalized = buffer.replace(/\r\n/g, '\n');
      const parts = normalized.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        const events = parseSseEvents(part);
        for (const event of events) {
          try {
            const payload = JSON.parse(event.data);
            switch (event.type) {
              case 'start':
                onStart?.(payload);
                break;
              case 'progress':
                onProgress?.(payload.result || payload);
                break;
              case 'complete':
                onComplete?.(payload);
                break;
              default:
                console.warn('Unknown event type:', event.type);
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', event.data, e);
          }
        }
      }
    }
  } catch (error) {
    console.error('Swarm service error:', error);
    onError?.(error);
    throw error;
  }
};
