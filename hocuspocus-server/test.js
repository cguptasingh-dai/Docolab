// hocuspocus-server/test.js
// Unit tests for auth and storage logic.
// Run: node --test test.js

import { describe, test } from 'node:test';
import assert from 'node:assert/strict';
import jwt from 'jsonwebtoken';

const SECRET = 'test-secret-for-unit-tests';

// ─────────────────────────────────────────────────────────────────────────────
// verifyToken logic (mirrors auth.js without DB)
// ─────────────────────────────────────────────────────────────────────────────

function verifyTokenSync(token, secret) {
  try {
    const payload = jwt.verify(token, secret, { algorithms: ['HS256'] });
    return { id: payload.sub, email: payload.email ?? payload.sub, org_id: payload.org_id };
  } catch {
    return null;
  }
}

describe('verifyToken', () => {
  test('returns user payload for a valid HS256 token', () => {
    const token = jwt.sign(
      { sub: 'user-abc', email: 'alice@example.com', org_id: 'org-1' },
      SECRET,
      { algorithm: 'HS256', expiresIn: '1h' }
    );
    const result = verifyTokenSync(token, SECRET);
    assert.equal(result?.id, 'user-abc');
    assert.equal(result?.email, 'alice@example.com');
    assert.equal(result?.org_id, 'org-1');
  });

  test('returns null for an expired token', () => {
    const token = jwt.sign({ sub: 'user-abc' }, SECRET, { expiresIn: 0 });
    const result = verifyTokenSync(token, SECRET);
    assert.equal(result, null);
  });

  test('returns null when signed with wrong secret', () => {
    const token = jwt.sign({ sub: 'user-abc' }, 'wrong-secret');
    const result = verifyTokenSync(token, SECRET);
    assert.equal(result, null);
  });

  test('returns null for a malformed token string', () => {
    const result = verifyTokenSync('not.a.valid.token', SECRET);
    assert.equal(result, null);
  });

  test('falls back email to sub when email claim is absent', () => {
    const token = jwt.sign({ sub: 'user-xyz', org_id: 'org-2' }, SECRET, {
      algorithm: 'HS256',
      expiresIn: '1h',
    });
    const result = verifyTokenSync(token, SECRET);
    assert.equal(result?.email, 'user-xyz');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// getUserRole fallback (mirrors auth.js role resolution logic)
// ─────────────────────────────────────────────────────────────────────────────

function resolveRole(docRows, folderRows) {
  if (docRows.length > 0) return docRows[0].name;
  if (folderRows.length > 0) return folderRows[0].name;
  return 'viewer';
}

describe('getUserRole fallback logic', () => {
  test('uses document-scoped role when present', () => {
    assert.equal(resolveRole([{ name: 'editor' }], []), 'editor');
  });

  test('falls back to folder-scoped role when no document assignment', () => {
    assert.equal(resolveRole([], [{ name: 'commenter' }]), 'commenter');
  });

  test('defaults to viewer when no assignment exists', () => {
    assert.equal(resolveRole([], []), 'viewer');
  });

  test('document scope takes precedence over folder scope', () => {
    assert.equal(resolveRole([{ name: 'admin' }], [{ name: 'viewer' }]), 'admin');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// storage.js type conversion (Uint8Array ↔ Buffer)
// ─────────────────────────────────────────────────────────────────────────────

describe('storage type conversion', () => {
  test('Buffer.from(Uint8Array) preserves bytes', () => {
    const input = new Uint8Array([0x01, 0x02, 0xff, 0x00]);
    const buf = Buffer.from(input);
    assert.ok(Buffer.isBuffer(buf));
    assert.deepEqual([...buf], [...input]);
  });

  test('new Uint8Array(Buffer) preserves bytes', () => {
    const buf = Buffer.from([0x10, 0x20, 0x30]);
    const arr = new Uint8Array(buf);
    assert.ok(arr instanceof Uint8Array);
    assert.deepEqual([...arr], [0x10, 0x20, 0x30]);
  });

  test('null yjs_state maps to null return (new document)', () => {
    const row = { yjs_state: null };
    const result = row.yjs_state ? new Uint8Array(row.yjs_state) : null;
    assert.equal(result, null);
  });

  test('non-null yjs_state maps to Uint8Array', () => {
    const row = { yjs_state: Buffer.from([1, 2, 3]) };
    const result = row.yjs_state ? new Uint8Array(row.yjs_state) : null;
    assert.ok(result instanceof Uint8Array);
    assert.deepEqual([...result], [1, 2, 3]);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// READ_ONLY_ROLES guard
// ─────────────────────────────────────────────────────────────────────────────

describe('READ_ONLY_ROLES', () => {
  const READ_ONLY_ROLES = new Set(['viewer']);

  test('viewer is read-only', () => {
    assert.ok(READ_ONLY_ROLES.has('viewer'));
  });

  test('editor is not read-only', () => {
    assert.ok(!READ_ONLY_ROLES.has('editor'));
  });

  test('admin is not read-only', () => {
    assert.ok(!READ_ONLY_ROLES.has('admin'));
  });

  test('commenter is not read-only', () => {
    assert.ok(!READ_ONLY_ROLES.has('commenter'));
  });
});
