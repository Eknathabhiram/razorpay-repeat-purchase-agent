import asyncio
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from . import schema as t
from .errors import ApplicationError

hasher = PasswordHasher()
dummy_digest = hasher.hash(secrets.token_urlsafe(32))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def session_csrf(token):
    # Stable across app reloads/tabs, without storing a plaintext token in DB.
    return hmac.new(token.encode(), b"repeat-purchase-csrf-v1", hashlib.sha256).hexdigest()


def check_password(stored, password):
    try:
        return hasher.verify(stored, password)
    except (VerificationError, InvalidHashError):
        return False


async def charge_login_attempt(db, login, ip):
    now = datetime.now(timezone.utc)
    # Persist counters even when the later login transaction rejects credentials.
    async with db.unit_of_work() as session:
        counts = []
        for key in sorted((digest("ip:" + ip), digest("login:" + login))):
            statement = insert(t.login_limits).values(bucket=key, attempts=1, window_start=now)
            recent = t.login_limits.c.window_start > now - timedelta(minutes=15)
            statement = statement.on_conflict_do_update(
                index_elements=[t.login_limits.c.bucket],
                set_={"attempts": sa.case((recent, t.login_limits.c.attempts + 1), else_=1),
                      "window_start": sa.case((recent, t.login_limits.c.window_start), else_=now)},
            ).returning(t.login_limits.c.attempts)
            counts.append(await session.scalar(statement))
    if max(counts) > 8:
        raise ApplicationError(429, "LOGIN_THROTTLED", "Too many login attempts. Try again in 15 minutes.")


async def authenticate(session, token):
    if not token:
        raise ApplicationError(401, "SESSION_REQUIRED", "Sign in to the application.")
    row = (await session.execute(sa.select(
        t.sessions.c.id.label("session_id"), t.sessions.c.csrf_hash,
        t.users.c.id.label("user_id"), t.users.c.login_identifier
    ).select_from(t.sessions.join(t.users, t.users.c.id == t.sessions.c.user_id)).where(
        t.sessions.c.token_hash == digest(token), t.sessions.c.revoked_at.is_(None),
        t.sessions.c.expires_at > datetime.now(timezone.utc), t.users.c.disabled_at.is_(None)
    ))).mappings().first()
    if not row:
        raise ApplicationError(401, "SESSION_REQUIRED", "Your session expired. Sign in again.")
    return row


def verify_csrf(actor, value):
    if not value or not secrets.compare_digest(actor["csrf_hash"], digest(value)):
        raise ApplicationError(403, "CSRF_INVALID", "Reload the review page and sign in again.")
