from pathlib import Path
import os
import shutil
import sys
import tempfile
import time
import uuid
from runtime import atomic_json,digest,entry,files,inside,parser,read_json

def temp_roots():
    roots=[Path(tempfile.gettempdir()).resolve()]
    if os.environ.get('WINDIR'):roots.append((Path(os.environ['WINDIR'])/'Temp').resolve())
    return roots

def scan(root,days=7):
    root=Path(root).resolve()
    if not 1<=days<=3650:raise ValueError('Wiek 1–3650 dni.')
    result=[]
    for path in files(root):
        st=path.stat()
        if st.st_mtime<time.time()-days*86400:
            result.append({'path':path.relative_to(root).as_posix(),'size':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':digest(path)})
    return {'schema_version':1,'root':str(root),'days':days,'files':result,'clean_allowed':root in temp_roots()}

def clean(plan,destination):
    root=Path(plan['root']).resolve();destination=Path(destination).resolve()
    if root not in temp_roots():raise ValueError('CLEAN dozwolone tylko w TEMP.')
    if destination.is_relative_to(root):raise ValueError('Kwarantanna musi być poza TEMP źródłowym.')
    # Wszystkie wpisy weryfikujemy przed pierwszą zmianą.
    for row in plan['files']:
        p=inside(root,row['path'])
        if not p.is_file() or p.stat().st_mtime>=time.time()-86400 or digest(p)!=row['sha256']:raise ValueError('Plan nieaktualny.')
    destination.mkdir(parents=True,exist_ok=False)
    manifest={'schema_version':1,'root':str(root),'files':[]}
    atomic_json(destination/'manifest.json',manifest)
    for row in plan['files']:
        source=inside(root,row['path'])
        if digest(source)!=row['sha256']:raise ValueError('Plik zmienił się przed przeniesieniem.')
        record={**row,'stored':uuid.uuid4().hex};manifest['files'].append(record)
        atomic_json(destination/'manifest.json',manifest)
        shutil.move(str(source),str(destination/record['stored']))
    return {'moved':len(manifest['files']),'quarantine':str(destination)}

def restore(directory):
    directory=Path(directory).resolve();data=read_json(directory/'manifest.json');root=Path(data['root']).resolve()
    if root not in temp_roots():raise ValueError('Nieprawidłowy root.')
    restored=0
    for row in data['files']:
        source=inside(directory,row['stored']);target=inside(root,row['path'])
        if not source.exists():continue
        if target.exists() or digest(source)!=row['sha256']:raise ValueError('Kolizja lub zmieniony plik kwarantanny.')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(source),str(target));restored+=1
    return {'restored':restored}

def build():
    p=parser('SCAN → PREVIEW → CLEAN. CLEAN oznacza kwarantannę z możliwością rollbacku.')
    p.add_argument('command',nargs='?',choices=['scan','preview','clean','restore'])
    p.add_argument('--root',default=tempfile.gettempdir());p.add_argument('--days',type=int,default=7)
    p.add_argument('--plan');p.add_argument('--quarantine');p.add_argument('--apply',action='store_true')
    return p

def handle(a):
    if a.command=='scan':
        data=scan(a.root,a.days)
        if a.plan:
            if Path(a.plan).exists():raise FileExistsError(a.plan)
            atomic_json(a.plan,data)
        return data
    if a.command in ('preview','clean'):
        if not a.plan:raise ValueError('Podaj --plan.')
        data=read_json(a.plan)
        if a.command=='preview' or not a.apply:return data
        if not a.quarantine:raise ValueError('Podaj nowy katalog --quarantine.')
        return clean(data,a.quarantine)
    if a.command=='restore':
        if not a.quarantine:raise ValueError('Podaj --quarantine.')
        return restore(a.quarantine) if a.apply else read_json(Path(a.quarantine)/'manifest.json')
    raise ValueError('Wybierz polecenie.')

if __name__=='__main__':sys.exit(entry(build,handle))
