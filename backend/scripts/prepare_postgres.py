"""Prepare an isolated, loopback-only PostgreSQL runtime. No Windows service."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local" / "postgres"
URL = "https://sbp.enterprisedb.com/getfile.jsp?fileid=1260609"


def run(*args):
    subprocess.run([str(x) for x in args], check=True, stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    LOCAL.mkdir(parents=True, exist_ok=True)
    binary = LOCAL / "pgsql" / "bin"
    if args.download and not (binary / "postgres.exe").exists():
        archive = LOCAL / "postgres.zip"
        if not archive.exists():
            print("Downloading official PostgreSQL 18 Windows archive...", flush=True)
            urllib.request.urlretrieve(URL, archive)
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                if member.filename.startswith(("pgsql/bin/", "pgsql/lib/", "pgsql/share/")):
                    destination = (LOCAL / member.filename).resolve()
                    if not destination.is_relative_to(LOCAL.resolve()):
                        raise RuntimeError("Archive path escapes runtime directory")
                    bundle.extract(member, LOCAL)
        (LOCAL / "download.json").write_text(json.dumps({
            "source": URL, "sha256": hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
        }, indent=2))
        print("PostgreSQL binaries extracted inside backend/.local.", flush=True)
    data = LOCAL / "data"
    if args.start:
        auth = LOCAL / "auth.json"
        if not auth.exists():
            auth.write_text(json.dumps({key: secrets.token_urlsafe(32)
                                       for key in ("admin", "migrator", "app")}))
        values = json.loads(auth.read_text())
        if not (data / "PG_VERSION").exists():
            password_file = LOCAL / "init-password"
            password_file.write_text(values["admin"], encoding="utf-8")
            try:
                run(binary / "initdb.exe", "-D", data, "-U", "rpa_admin",
                    "--pwfile", password_file, "--auth=scram-sha-256", "--encoding=UTF8",
                    "--locale=C")
            finally:
                password_file.unlink(missing_ok=True)
            with (data / "postgresql.conf").open("a", encoding="utf-8") as config:
                config.write("\nlisten_addresses = '127.0.0.1'\nport = 55432\n")
        state = subprocess.run([str(binary / "pg_ctl.exe"), "-D", str(data), "status"],
                               stdout=subprocess.DEVNULL)
        if state.returncode:
            run(binary / "pg_ctl.exe", "-D", data, "-l", LOCAL / "server.log", "-w", "start")
        import psycopg
        from psycopg import sql
        with psycopg.connect(host="127.0.0.1", port=55432, user="rpa_admin",
                             password=values["admin"], dbname="postgres", autocommit=True) as conn:
            for role in ("migrator", "app"):
                name = "rpa_" + role
                if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (name,)).fetchone():
                    conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS").format(
                        sql.Identifier(name), sql.Literal(values[role])))
            for name in ("rpa_development", "rpa_stage1_test"):
                if not conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone():
                    conn.execute(sql.SQL("CREATE DATABASE {} OWNER rpa_migrator").format(sql.Identifier(name)))
        settings = ROOT / ".env.foundation"
        if not settings.exists():
            settings.write_text(
                f"APP_DATABASE_URL=postgresql+psycopg://rpa_app:{values['app']}@127.0.0.1:55432/rpa_development\n"
                f"MIGRATION_DATABASE_URL=postgresql+psycopg://rpa_migrator:{values['migrator']}@127.0.0.1:55432/rpa_development\n"
                "APP_ALLOWED_HOSTS=127.0.0.1,localhost\n"
                "APP_ALLOWED_ORIGINS=http://127.0.0.1:8766,http://localhost:8766\n", encoding="utf-8")
        print("PostgreSQL running on loopback :55432; development/test databases ready.", flush=True)
    if args.stop:
        run(binary / "pg_ctl.exe", "-D", data, "-w", "stop", "-m", "fast")
        print("Project PostgreSQL stopped.")


if __name__ == "__main__":
    main()
