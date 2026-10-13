"""Private local backup/restore proof. Never restore over the development database."""
import json,os,subprocess,uuid
from pathlib import Path
from app.settings import BACKEND,Settings
from sqlalchemy.engine import make_url
import psycopg
from psycopg import sql

def main():
    url=make_url(Settings.from_environment().database_url)
    if url.host not in ('127.0.0.1','localhost') or url.port!=55432 or url.database!='rpa_development':
        raise RuntimeError('Backup rehearsal only accepts the known loopback development database')
    auth=json.loads((BACKEND/'.local/postgres/auth.json').read_text())
    bins=BACKEND/'.local/postgres/pgsql/bin'
    dump=BACKEND/'.local/release-rehearsal.dump'
    env={**os.environ,'PGPASSWORD':auth['admin']}
    admin_user='rpa_admin'
    target='rpa_restore_probe_'+uuid.uuid4().hex[:10]
    def run_tool(name,args):
        result=subprocess.run([str(bins/(name+'.exe')),*args],env=env,capture_output=True,timeout=90)
        if result.returncode:raise RuntimeError(name+' failed; private diagnostics withheld')
    admin=psycopg.connect(host='127.0.0.1',port=55432,dbname='postgres',user=admin_user,password=auth['admin'],autocommit=True)
    try:
        run_tool('pg_dump',['-h','127.0.0.1','-p','55432','-U',admin_user,'-Fc','-f',str(dump),'rpa_development'])
        with admin.cursor() as cur:cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(target)))
        run_tool('pg_restore',['-h','127.0.0.1','-p','55432','-U',admin_user,'--exit-on-error','-d',target,str(dump)])
        counts={}
        for name in ('rpa_development',target):
            with psycopg.connect(host='127.0.0.1',port=55432,dbname=name,user=admin_user,password=auth['admin']) as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT version_num FROM alembic_version');revision=cur.fetchone()[0]
                    counts[name]={'revision':revision}
                    for table in ('workspaces','journeys','confirmed_purchases','cohort_assignments','intelligence_turns'):
                        cur.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)));counts[name][table]=cur.fetchone()[0]
        assert counts['rpa_development']==counts[target]
        output={'status':'passed','revision':counts[target]['revision'],'counts_match':True,'restored_tables_checked':5,'restored_to_new_disposable_database':True,'owner_database_modified':False,'backup_location':'private backend/.local/release-rehearsal.dump'}
        (BACKEND.parent/'docs/implementation-evidence/stage-09-backup.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
        print(json.dumps(output))
    finally:
        if not target.startswith('rpa_restore_probe_'):raise RuntimeError('Invalid cleanup target')
        with admin.cursor() as cur:cur.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(target)))
        admin.close()

if __name__=='__main__':main()
