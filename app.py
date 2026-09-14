from pathlib import Path
import os
import shutil
import sys
import tempfile
import time
import uuid
from runtime import atomic_json,digest,entry,files,inside,parser,powershell,read_json

def temp_roots():
    roots=[Path(tempfile.gettempdir()).resolve()]
    if os.environ.get('WINDIR'):roots.append((Path(os.environ['WINDIR'])/'Temp').resolve())
    return roots

def profiles():
    result={'temp':str(Path(tempfile.gettempdir()).resolve())}
    if os.environ.get('WINDIR'):
        result['windows-temp']=str(Path(os.environ['WINDIR'])/'Temp')
        result['windows-logs']=str(Path(os.environ['WINDIR'])/'Logs')
    if os.environ.get('LOCALAPPDATA'):
        result['directx-cache']=str(Path(os.environ['LOCALAPPDATA'])/'D3DSCache')
        result['thumbnails']=str(Path(os.environ['LOCALAPPDATA'])/'Microsoft/Windows/Explorer')
    result['downloads']=str(Path.home()/'Downloads')
    if os.name=='nt':result['recycle-bin']='Kosz bieżącego użytkownika — analiza'
    return result

def scan_recycle():
    if os.name!='nt':raise ValueError('Odczyt kosza wymaga Windows.')
    rows=powershell(r'''$shell=New-Object -ComObject Shell.Application;$bin=$shell.NameSpace(10)
if($null -eq $bin){throw 'Kosz niedostępny.'}
$rows=@(foreach($item in $bin.Items()){[pscustomobject]@{name=[string]$item.Name;size=[long]$item.Size;is_folder=[bool]$item.IsFolder;deleted=[string]$item.ExtendedProperty('System.Recycle.DateDeleted')}})
ConvertTo-Json -InputObject $rows -Depth 4''')
    return {'schema_version':1,'kind':'recycle-bin','analysis_only':True,'items':rows or [],
        'clean_allowed':False,'note':'Analiza kosza. Trwałe opróżnianie wymaga osobnego planu i jawnej zgody w Windows Toolkit; brak rollbacku.'}

def can_clean(root,relative):
    root=Path(root).resolve()
    if root in temp_roots():return True
    known=profiles()
    if 'directx-cache' in known and root==Path(known['directx-cache']).resolve():return True
    if 'thumbnails' in known and root==Path(known['thumbnails']).resolve():
        return Path(relative).parent==Path('.') and Path(relative).name.startswith('thumbcache_') and Path(relative).suffix.lower()=='.db'
    return False

def scan(root,days=7):
    root=Path(root).resolve()
    if not 1<=days<=3650:raise ValueError('Wiek 1–3650 dni.')
    result=[]
    for path in files(root):
        st=path.stat()
        if st.st_mtime<time.time()-days*86400:
            relative=path.relative_to(root).as_posix()
            categories=[]
            if st.st_size>=100*1024*1024:categories.append('large')
            if path.suffix.lower() in ('.msi','.msix','.exe','.iso'):categories.append('installer_or_image')
            if path.suffix.lower() in ('.log','.etl','.evtx'):categories.append('log')
            result.append({'path':relative,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':digest(path),'categories':categories,'clean_allowed':can_clean(root,relative)})
    return {'schema_version':1,'root':str(root),'days':days,'files':result,'clean_allowed':bool(result) and all(row['clean_allowed'] for row in result),'total_bytes':sum(row['size'] for row in result)}

def clean(plan,destination):
    root=Path(plan['root']).resolve();destination=Path(destination).resolve()
    known=profiles()
    allowed_roots=temp_roots()+[Path(known[key]).resolve() for key in ('directx-cache','thumbnails') if key in known]
    if root not in allowed_roots:raise ValueError('CLEAN poza zatwierdzonym katalogiem.')
    if not isinstance(plan.get('files'),list) or any(not can_clean(root,row['path']) for row in plan['files']):raise ValueError('CLEAN dozwolone tylko dla zatwierdzonych plików TEMP/cache.')
    if not plan['files']:return {'moved':0,'quarantine':None}
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
    if any(not can_clean(root,row['path']) for row in data['files']):raise ValueError('Nieprawidłowy root lub plik.')
    # Kolizje sprawdzamy przed pierwszym odtworzeniem.
    for row in data['files']:
        source=inside(directory,row['stored']);target=inside(root,row['path'])
        if source.exists() and (target.exists() or digest(source)!=row['sha256']):raise ValueError('Kolizja lub zmieniony plik kwarantanny.')
    restored=0
    for row in data['files']:
        source=inside(directory,row['stored']);target=inside(root,row['path'])
        if not source.exists():continue
        if target.exists() or digest(source)!=row['sha256']:raise ValueError('Kolizja lub zmieniony plik kwarantanny.')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(source),str(target));restored+=1
    return {'restored':restored}

def build():
    p=parser('SCAN → PREVIEW → CLEAN. CLEAN oznacza kwarantannę z możliwością rollbacku.')
    p.add_argument('command',nargs='?',choices=['scan','preview','clean','restore','profiles'])
    p.add_argument('--profile',choices=['temp','windows-temp','directx-cache','thumbnails','windows-logs','downloads','recycle-bin'])
    p.add_argument('--root',default=tempfile.gettempdir());p.add_argument('--days',type=int,default=7)
    p.add_argument('--plan');p.add_argument('--quarantine');p.add_argument('--apply',action='store_true')
    return p

def handle(a):
    if a.command=='profiles':return profiles()
    if a.command=='scan':
        if a.profile=='recycle-bin':
            data=scan_recycle()
            if a.plan:
                if Path(a.plan).exists():raise FileExistsError(a.plan)
                atomic_json(a.plan,data)
            return data
        if a.profile:
            if a.profile not in profiles():raise ValueError('Profil niedostępny w tym systemie.')
            a.root=profiles()[a.profile]
        data=scan(a.root,a.days)
        if a.profile=='thumbnails':
            data['files']=[row for row in data['files'] if row['clean_allowed']]
            data['total_bytes']=sum(row['size'] for row in data['files'])
            data['clean_allowed']=True
        if a.plan:
            if Path(a.plan).exists():raise FileExistsError(a.plan)
            atomic_json(a.plan,data)
        return data
    if a.command in ('preview','clean'):
        if not a.plan:raise ValueError('Podaj --plan.')
        data=read_json(a.plan)
        if a.command=='preview' or not a.apply:return data
        if data.get('analysis_only'):raise ValueError('Ten plan służy wyłącznie do analizy; nie pozwala na CLEAN.')
        if not a.quarantine:raise ValueError('Podaj nowy katalog --quarantine.')
        return clean(data,a.quarantine)
    if a.command=='restore':
        if not a.quarantine:raise ValueError('Podaj --quarantine.')
        return restore(a.quarantine) if a.apply else read_json(Path(a.quarantine)/'manifest.json')
    raise ValueError('Wybierz polecenie.')

if __name__=='__main__':sys.exit(entry(build,handle))
