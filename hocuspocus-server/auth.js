// hocuspocus-server/auth.js
// JWT verification + role resolution.
// Uses the same JWT_SECRET and role/assignment tables as the FastAPI backend.

import jwt from "jsonwebtoken";
import { query } from "./db.js";

const JWT_SECRET = process.env.JWT_SECRET ?? "changeme-use-same-secret-as-fastapi";

// ─────────────────────────────────────────────────────────────────────────────
// verifyToken(token) → { id, email, org_id } | null
// Decodes and validates the access JWT issued by POST /auth/login.
// ─────────────────────────────────────────────────────────────────────────────
export async function verifyToken(token) {
  try {
    const payload = jwt.verify(token, JWT_SECRET, { algorithms: ["HS256"] });
    // Payload shape from FastAPI: { sub: user_id, org_id, email, exp }
    return {
      id: payload.sub,
      email: payload.email ?? payload.sub,
      org_id: payload.org_id,
    };
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// getUserRole(userId, documentId, orgId) → role name string
// Walks the same assignments→roles chain the FastAPI authorize() uses.
// Falls back to "viewer" if no assignment found (safe default).
// ─────────────────────────────────────────────────────────────────────────────
export async function getUserRole(userId, documentId, orgId) {
  // 1. Check for a document-scoped assignment first (most specific)
  const docResult = await query(
    `SELECT r.name
       FROM assignments a
       JOIN roles r ON r.id = a.role_id
      WHERE a.user_id = $1
        AND a.scope_type = 'document'
        AND a.scope_id = $2
        AND a.org_id = $3
      LIMIT 1`,
    [userId, documentId, orgId]
  );
  if (docResult.rows.length > 0) return docResult.rows[0].name;

  // 2. Fall back to the folder-scoped assignment for the document's folder
  const folderResult = await query(
    `SELECT r.name
       FROM assignments a
       JOIN roles r ON r.id = a.role_id
       JOIN documents d ON d.folder_id = a.scope_id
      WHERE a.user_id = $1
        AND a.scope_type = 'folder'
        AND d.id = $2
        AND a.org_id = $3
      LIMIT 1`,
    [userId, documentId, orgId]
  );
  if (folderResult.rows.length > 0) return folderResult.rows[0].name;

  // 3. No assignment found — safe read-only default
  return "viewer";
}
