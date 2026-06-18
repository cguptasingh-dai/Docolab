// hocuspocus-server/server.js
// Real-time collaboration server for Docolab.
//
// Responsibilities:
//   1. Authenticate each WebSocket connection using the same JWT the REST API issues
//   2. Load the Y.Doc for a document from PostgreSQL when the first client connects
//   3. Broadcast Yjs binary updates between all connected clients in real time
//   4. Persist the updated Y.Doc back to PostgreSQL (debounced)
//   5. Set connection as read-only for viewer roles
//
// The REST API (FastAPI) never touches document content — it handles governance only.
// This server handles content only — it never touches governance.

import "dotenv/config";
import { Server } from "@hocuspocus/server";
import { verifyToken, getUserRole } from "./auth.js";
import { loadDocument, storeDocument } from "./storage.js";

const PORT = parseInt(process.env.COLLAB_PORT ?? "1234", 10);

// Read-only roles — these users can receive updates but cannot push edits
const READ_ONLY_ROLES = new Set(["viewer"]);

const server = Server.configure({
  port: PORT,
  timeout: 30000,           // disconnect idle clients after 30s
  debounce: 2000,           // wait 2s of inactivity before calling onStoreDocument
  maxDebounce: 10000,       // always store within 10s even if client keeps typing

  // ──────────────────────────────────────────────────────────────────────────
  // 1. AUTHENTICATE
  // Called once per WebSocket connection, before any document data is sent.
  // Throws → connection rejected with 403.
  // ──────────────────────────────────────────────────────────────────────────
  async onAuthenticate({ token, documentName, connection }) {
    if (!token) throw new Error("No token provided");

    const user = await verifyToken(token);
    if (!user) throw new Error("Invalid or expired token");

    // documentName is the document UUID (set from the frontend provider config)
    const role = await getUserRole(user.id, documentName, user.org_id);

    // Store on the connection context so other hooks can read it
    connection.context = { user, role };

    // Read-only connections can receive updates but cannot send edits
    connection.readOnly = READ_ONLY_ROLES.has(role);

    console.log(
      `[auth] user=${user.email} doc=${documentName} role=${role} readOnly=${connection.readOnly}`
    );
  },

  // ──────────────────────────────────────────────────────────────────────────
  // 2. LOAD DOCUMENT
  // Called when the first client connects to a documentName and Hocuspocus has
  // no in-memory state for it. Return the stored Yjs state vector (Uint8Array)
  // or null to start with a blank document.
  // ──────────────────────────────────────────────────────────────────────────
  async onLoadDocument({ documentName, document }) {
    const stored = await loadDocument(documentName);
    if (stored) {
      // Apply the saved binary state to the in-memory Y.Doc
      const { applyUpdate } = await import("yjs");
      applyUpdate(document, stored);
      console.log(`[load] doc=${documentName} bytes=${stored.byteLength}`);
    } else {
      console.log(`[load] doc=${documentName} new document`);
    }
    return document;
  },

  // ──────────────────────────────────────────────────────────────────────────
  // 3. STORE DOCUMENT
  // Called after the debounce window when the document has been modified.
  // Serialises the full Y.Doc state and writes it to PostgreSQL.
  // ──────────────────────────────────────────────────────────────────────────
  async onStoreDocument({ documentName, document }) {
    const { encodeStateAsUpdate } = await import("yjs");
    const state = encodeStateAsUpdate(document);
    await storeDocument(documentName, state);
    console.log(`[store] doc=${documentName} bytes=${state.byteLength}`);
  },

  // ──────────────────────────────────────────────────────────────────────────
  // 4. ON CONNECT / DISCONNECT (logging only)
  // ──────────────────────────────────────────────────────────────────────────
  async onConnect({ documentName, connection }) {
    const ctx = connection.context ?? {};
    console.log(`[connect] doc=${documentName} user=${ctx.user?.email ?? "unknown"}`);
  },

  async onDisconnect({ documentName, connection }) {
    const ctx = connection.context ?? {};
    console.log(`[disconnect] doc=${documentName} user=${ctx.user?.email ?? "unknown"}`);
  },
});

server.listen();
console.log(`Hocuspocus listening on ws://localhost:${PORT}`);
