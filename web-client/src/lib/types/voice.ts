// ──────────────────────────────────────────────────────────────────────────────
// InsightDesk AI — Voice Schemas (TypeScript mirror)
// Source of truth: shared/schemas/voice.py
// ──────────────────────────────────────────────────────────────────────────────

export interface ICEServer {
  urls: string[];
  username?: string | null;
  credential?: string | null;
}

export interface WebRTCConfig {
  iceServers: ICEServer[];
  sdpSemantics: string;
  bundlePolicy: string;
}

export interface SDPOffer {
  type: "offer";
  sdp: string;
}

export interface SDPAnswer {
  type: "answer";
  sdp: string;
}

export interface ICECandidate {
  candidate: string;
  sdpMid?: string | null;
  sdpMLineIndex?: number | null;
  usernameFragment?: string | null;
}

export enum SessionStatus {
  INITIALIZING = "initializing",
  NEGOTIATING = "negotiating",
  CONNECTED = "connected",
  STREAMING = "streaming",
  DISCONNECTED = "disconnected",
  ERROR = "error",
}

export interface VoiceSession {
  session_id: string;
  status: SessionStatus;
  ttfa_ms?: number | null;
  jitter_ms?: number | null;
  packet_loss_pct?: number | null;
  mos_score?: number | null;
}

export interface AudioChunk {
  session_id: string;
  sequence: number;
  codec: string;
  sample_rate: number;
  channels: number;
  payload_b64: string;
  is_barge_in: boolean;
}
