/**
 * Genesis Engine - WebSocket Client Manager
 * Manages real-time bidirectional communication with the Maestro Loop.
 * SPEC §4.2 WebSocket Channel Compliance
 */

export type SandboxState = 
  | 'IDLE' 
  | 'SPARK_RECEIVED' 
  | 'REASONING' 
  | 'CALLING_CHARACTER' 
  | 'EVALUATING' 
  | 'EMITTING_IR' 
  | 'RENDERING' 
  | 'COMMITTED' 
  | 'INTERRUPTED';

export interface WSEvent {
  type: string;
  payload: Record<string, unknown>;
}

type EventHandler = (payload: Record<string, unknown>) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private _url: string;
  private _isConnected = false;

  constructor(url?: string) {
    this._url = url || `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
  }

  get isConnected(): boolean {
    return this._isConnected;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) return;

    try {
      this.ws = new WebSocket(this._url);

      this.ws.onopen = () => {
        this._isConnected = true;
        console.log('[WS] Connected to Genesis Engine');
        this.emit('CONNECTION_STATUS', { connected: true });
      };

      this.ws.onmessage = (event) => {
        try {
          const parsed: WSEvent = JSON.parse(event.data);
          if (parsed.type) {
            this.emit(parsed.type, parsed.payload || {});
          }
        } catch (e) {
          console.error('[WS] Failed to parse message:', e);
        }
      };

      this.ws.onclose = (event) => {
        this._isConnected = false;
        // Only reconnect if it wasn't a clean, intentional closure
        if (this.ws) {
          console.log('[WS] Disconnected. Reconnecting in 3s...');
          this.emit('CONNECTION_STATUS', { connected: false });
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (err) => {
        // Only log error if we're not in the middle of a manual disconnect
        if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
          console.error('[WS] Error:', err);
        }
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      // Remove handlers before closing to prevent errors/reconnects during intentional shutdown
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onerror = null;
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this._isConnected = false;
  }

  // ===========================
  // Upstream Commands (SPEC §4.2)
  // ===========================

  /** Send CUT command to interrupt the Maestro Loop */
  sendCut(sparkId: string): void {
    this.send({ Action: 'CUT', spark_id: sparkId });
  }

  /** Send OVERRIDE directive to inject God Mode instructions */
  sendOverride(sparkId: string, entityId: string, newDirective: string): void {
    this.send({
      Action: 'OVERRIDE',
      spark_id: sparkId,
      entity_id: entityId,
      new_directive: newDirective,
    });
  }

  // ===========================
  // Pub/Sub Event System
  // ===========================

  on(event: string, handler: EventHandler): () => void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.handlers.get(event)?.delete(handler);
    };
  }

  private emit(event: string, data: Record<string, unknown>): void {
    this.handlers.get(event)?.forEach((handler) => {
      try {
        handler(data);
      } catch (e) {
        console.error(`[WS] Handler error for event "${event}":`, e);
      }
    });
  }

  private send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('[WS] Cannot send - not connected');
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) return;
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, 3000);
  }
}

// Singleton for app-wide usage
export const wsManager = new WebSocketManager();
