#!/usr/bin/env python3
"""Exact additive seven-preview build; no network, deployment, rebasing or base edits.
The original 1870 exporter is loaded unchanged and its complete output is preserved.
"""
from pathlib import Path,PurePosixPath
from html.parser import HTMLParser
from dataclasses import dataclass
import argparse,hashlib,importlib.util,json,os,re,stat,sys,tempfile,zipfile
BASE_EXPORTER_SHA256='a87f189f4878decbc392f41b04a53f4d3e5144816d3084cea29ba850642aca04'
BASE_MANIFEST_SHA256='7c7ab5e0c1b010203ab92bc641ada4005b0588c80584b886ca8b3ead5af8e1ac'
QA_MANIFEST_SHA256='667d4ea8c6008bf19f1f03da7200d16335710a4cc93b08f41842747d4d28c539'
# Final exact names, sizes and SHA-256 values must be separately reviewed and frozen.
EXACT_QA_ARCHIVE_NAMES=('qa7-001.zip', 'qa7-002.zip', 'qa7-003.zip', 'qa7-004.zip', 'qa7-005.zip')
QA_ARCHIVE_RECORDS=(('qa7-001.zip', 7392771, 'd3dcef9543d5a599d6e1f939d81a4dfe9c2d71fb11ead26f7c91b73b46e3448e'), ('qa7-002.zip', 7396853, 'ae451b83c68f7ef70bafbf95d1a225558276b315de7147cdf88c92ef8825a673'), ('qa7-003.zip', 7227557, '7d8d53efcb9fd288ff7231b8f776f3fd84b92c91aea574b79cc5529e69572fb4'), ('qa7-004.zip', 7319713, '391e5c95de78bc12865c334eb470980ba0d966130070b0d96bed6ab64c1dc306'), ('qa7-005.zip', 7290501, 'c7c01df528dacdf5983078602d3be605b75e5bf8423c28451dfdd654f3fab8d7'))
BASE_FILE_COUNT=19150
QA_FILE_COUNT=192
COMBINED_FILE_COUNT=19342
FILE_CAP=20000
MAX_FILE_BYTES=10_000_000
MAX_PACK_BYTES=8*1024*1024
MAX_QA_BYTES=50_000_000
MAX_TOTAL_BYTES=900_000_000
PREFIX='qa-20261025'
ROUTES={'restaurants':frozenset(('8th-st-coffee-house','frank-joes-coffee-house-parker-square','frank-joes-coffee-house-southwest-parkway','the-duck-coffee-company')),'barbers':frozenset(('city-barbers-stylists','drews-barbershop-on-pershing','viva-307-barbershop'))}
CATEGORY_COUNTS={'restaurants':86,'barbers':106}
EXTENSIONS=frozenset(('.html','.css','.js','.svg','.png','.jpg','.jpeg','.webp','.ico','.ttf','.woff','.woff2','.webmanifest','.mp4'))
BRAND_FILES=frozenset(('apple-touch-icon.png','favicon.ico','icon-192.png','icon-256.png','icon-512.png','mark.png','preview.jpg','wordmark.png'))
# Explicit source MP4 set (not derived from an arbitrary supplied manifest).
MP4_RECORDS=(('barbers','0acf5959ba6219f3e9c8782db180fc831837f8a0dbe0c202341a670b26c71582',1104222),('barbers','26a8e7e00bec5499f17b38ba50dd88ace06e7f5bb0b0b238a79758da368437e0',1960401),('barbers','7c15b8aaac6a299db4c536a5881d4c0a3a93fa6f21633abd2dca507112e24345',1088771),('barbers','7cc6598e5c43c74443264fbde8a524c8c62760f3ce45e91460fce7a9526f8546',1406287),('restaurants','5df38d6223b0b5d6851b433ab71e27a2fb79005b4932b7bfb9850171f563b608',1342966),('restaurants','63c28b0b833d8b4b99d6ef1e02dfeb34d6c5acd3745d9e993c6bf84ec86ebcda',595817),('restaurants','a96d6031e9af134fae64ec65921fdb9a832746dbf50cd4940232f6f65af6c752',708507),('restaurants','f669f1e75c7498e69cacac58bcff156cd2419e3d51e1d6108bf5c4d8d5a187eb',1307185),('restaurants','f6903f735fb8a2223ab800f786572c22ca3709410c2ba8584f4b2142a74ba410',992053))
MP4_EXPECTED={f'{PREFIX}/{category}/assets/{h}.mp4':(size,h)for category,h,size in MP4_RECORDS}
HOME_PATHS=frozenset(f'{PREFIX}/{c}/{route}/index.html'for c,routes in ROUTES.items()for route in routes)
SHA=re.compile('[0-9a-f]{64}\\Z')

def require(ok,message):
 if not ok:raise ValueError(message)

def digest(data):return hashlib.sha256(data).hexdigest()

def digest_file(path):
 with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def strict_object(pairs):
 out={}
 for k,v in pairs:
  require(k not in out,'Duplicate JSON key');out[k]=v
 return out

def integer(n):return type(n)is int and n>=0

def safe_components(path):
 p=Path(path).absolute()
 for part in [*reversed(p.parents),p]:require(not part.is_symlink(),'Symlink path component rejected')
 return p

def regular_file(path):
 p=safe_components(path);require(p.is_file()and stat.S_ISREG(p.stat().st_mode),'Nonregular input rejected');return p

@dataclass(frozen=True)
class QAProfile:
 manifest_sha256:str
 archive_records:tuple

def frozen_profile():
 require(SHA.fullmatch(QA_MANIFEST_SHA256) is not None,'UNFROZEN QA manifest; no inputs read or output created')
 require(tuple(r[0]for r in QA_ARCHIVE_RECORDS)==EXACT_QA_ARCHIVE_NAMES,'Exactly the five reviewed QA archives required')
 names=[]
 for name,size,h in QA_ARCHIVE_RECORDS:
  require(isinstance(name,str)and re.fullmatch('[a-z0-9-]+\\.zip',name)and name not in names and integer(size)and 0<size<=MAX_PACK_BYTES and isinstance(h,str)and SHA.fullmatch(h),'UNFROZEN QA archive identity')
  names.append(name)
 return QAProfile(QA_MANIFEST_SHA256,QA_ARCHIVE_RECORDS)

def allowed_path(name):
 if not isinstance(name,str)or len(name)>240 or not re.fullmatch('[a-zA-Z0-9_./-]+',name):return False
 if PurePosixPath(name).as_posix()!=name or any(x in ('','.','..')or x.startswith('.') for x in name.split('/')):return False
 p=PurePosixPath(name);parts=p.parts
 if len(parts)<3 or parts[0]!=PREFIX or parts[1]not in ROUTES:return False
 tail=parts[2:];category=parts[1]
 if len(tail)==1:return tail[0]in {'index.html','robots.txt'}
 if tail[0]=='assets':return len(tail)==2 and bool(re.fullmatch('[0-9a-f]{40,64}\\.[a-z0-9]+',tail[1]))and p.suffix in EXTENSIONS and (p.suffix!='.mp4'or name in MP4_EXPECTED)
 if tail[0]not in ROUTES[category]:return False
 if len(tail)==2:return tail[1]in ({'index.html','robots.txt','sw.js'}if category=='barbers'else {'index.html'})
 if category=='restaurants'and len(tail)==3:return tail[1]in {'privacy','terms'}and tail[2]=='index.html'
 if category=='barbers'and len(tail)==3 and tail[1]=='assets':return tail[2]in {'rl-extras.js','site.webmanifest'}
 return len(tail)==4 and tail[1:3]==('assets','brand')and tail[3]in BRAND_FILES

class NoIndex(HTMLParser):
 def __init__(self):super().__init__();self.present=False
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=='meta'and d.get('name','').lower()=='robots'and 'noindex'in [x.strip().lower()for x in d.get('content','').split(',')]:self.present=True

def exact_qa_directory(folder,profile):
 folder=safe_components(folder);require(folder.is_dir(),'QA directory missing')
 names=set()
 for p in folder.iterdir():regular_file(p);names.add(p.name)
 require(names=={'manifest.json',*(r[0]for r in profile.archive_records)},'Extra or missing QA inputs')
 return folder

def member_guard(info,expected,seen):
 mode=info.external_attr>>16;name=info.filename
 require(not info.is_dir()and stat.S_ISREG(mode)and not info.flag_bits&0x41 and not info.extra,'Directory/link/special/encrypted/extra-field member rejected')
 require(info.compress_type in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED},'Unsupported compression')
 require(allowed_path(name)and name in expected and name not in seen,'Unsafe/duplicate/unexpected member')
 require(info.file_size==expected[name]['size']and info.file_size<=MAX_FILE_BYTES,'Wrong/oversized member')
 return name

def read_verified_member(archive,info,record,destination=None):
 size=0;h=hashlib.sha256();head=b'';metadata=[] if info.filename.endswith(('.html','robots.txt'))else None
 with archive.open(info)as source:
  while chunk:=source.read(1024*1024):
   size+=len(chunk);require(size<=record['size']and size<=MAX_FILE_BYTES,'Member expansion exceeded exact bound');h.update(chunk)
   if len(head)<32:head=(head+chunk)[:32]
   if metadata is not None:metadata.append(chunk)
   if destination is not None:destination.write(chunk)
 require(size==record['size']and h.hexdigest()==record['sha256'],'Member content hash/size mismatch')
 if info.filename.endswith('.mp4'):
  require(MP4_EXPECTED.get(info.filename)==(size,h.hexdigest()),'Exact reviewed MP4 mismatch')
  require(head[4:8]==b'ftyp'and head[8:12]==b'isom'and b'avc1'in head,'MP4 MIME/codec signature mismatch')
 if metadata is not None:
  text=b''.join(metadata).decode('utf-8')
  if info.filename.endswith('.html'):
   parser=NoIndex();parser.feed(text);require(parser.present,'QA HTML lacks actual noindex metadata')
  else:require(re.search(r'^\s*Disallow:\s*/\s*$',text,re.M),'QA robots exclusion missing')

def validate_qa(folder,profile):
 folder=exact_qa_directory(folder,profile);mf=regular_file(folder/'manifest.json');require(mf.stat().st_size<=2_000_000,'Oversized QA manifest');raw=mf.read_bytes();require(digest(raw)==profile.manifest_sha256,'Exact QA manifest mismatch');m=json.loads(raw,object_pairs_hook=strict_object)
 keys={'format','profile','base_manifest_sha256','base_exporter_sha256','base_file_count','qa_file_count','combined_file_count','business_preview_count','prefixes','homepages','archives','files'}
 require(isinstance(m,dict)and set(m)==keys,'QA manifest schema')
 for key,value in [('format',1),('base_file_count',BASE_FILE_COUNT),('qa_file_count',QA_FILE_COUNT),('combined_file_count',COMBINED_FILE_COUNT),('business_preview_count',7)]:require(type(m[key])is int and m[key]==value,'Exact QA profile count/version: '+key)
 require(m['profile']=='qa7-20261025'and m['base_manifest_sha256']==BASE_MANIFEST_SHA256 and m['base_exporter_sha256']==BASE_EXPORTER_SHA256,'Exact source profile pins')
 require(m['prefixes']==[PREFIX+'/restaurants/',PREFIX+'/barbers/'],'Exact QA prefixes')
 require(isinstance(m['homepages'],list)and len(m['homepages'])==7 and all(isinstance(x,str)for x in m['homepages'])and set(m['homepages'])==HOME_PATHS,'Exact seven reviewed homepages')
 require(isinstance(m['files'],list)and len(m['files'])==QA_FILE_COUNT,'QA file list count')
 expected={}
 for r in m['files']:
  require(isinstance(r,dict)and set(r)=={'path','bytes','sha256'},'QA file record schema');name=r['path']
  require(allowed_path(name)and name not in expected,'Unsafe or duplicate QA path');require(integer(r['bytes'])and r['bytes']<=MAX_FILE_BYTES and isinstance(r['sha256'],str)and SHA.fullmatch(r['sha256']),'Invalid file size/hash');expected[name]={'path':name,'size':r['bytes'],'sha256':r['sha256']}
 require(sum(r['size']for r in expected.values())<=MAX_QA_BYTES,'QA byte cap')
 require({c:sum(p.split('/')[1]==c for p in expected)for c in ROUTES}==CATEGORY_COUNTS,'Exact category file counts')
 require(HOME_PATHS<=expected.keys(),'Seven reviewed homepage paths required')
 require({p:(r['size'],r['sha256'])for p,r in expected.items()if p.endswith('.mp4')}==MP4_EXPECTED,'Exact nine QA MP4 set required')
 require(isinstance(m['archives'],list)and all(isinstance(x,dict)and set(x)=={'name','bytes','sha256','files'}for x in m['archives']),'QA archive schema')
 require(tuple((x['name'],x['bytes'],x['sha256'])for x in m['archives'])==profile.archive_records,'Exact QA archive names/order/size/hash pins')
 seen=set();verified=[]
 for entry,(name,size,h) in zip(m['archives'],profile.archive_records):
  member_names=entry['files'];require(isinstance(member_names,list)and member_names and all(isinstance(n,str)for n in member_names)and len(member_names)==len(set(member_names)),'Invalid archive member list')
  wanted=set(member_names);require(wanted<=set(expected)and not wanted&seen,'Invalid or duplicate archive member ownership')
  require(integer(size)and 0<size<=MAX_PACK_BYTES,'QA archive exceeds exact8MiB transport cap')
  p=regular_file(folder/name);require(p.stat().st_size==size and digest_file(p)==h,'QA archive identity mismatch');archive_seen=set()
  with zipfile.ZipFile(p)as archive:
   require(not archive.comment,'Unexpected ZIP comment')
   for info in archive.infolist():
    name=member_guard(info,expected,seen);require(name in wanted,'Archive member outside its exact reviewed ownership list');read_verified_member(archive,info,expected[name]);seen.add(name);archive_seen.add(name)
  require(archive_seen==wanted,'Missing archive members');verified.append(p)
 require(seen==set(expected),'Missing QA archive members')
 return m,expected,verified


def recheck_qa(folder,profile,manifest):
 exact_qa_directory(folder,profile);require(digest(regular_file(folder/'manifest.json').read_bytes())==profile.manifest_sha256,'QA manifest changed during build')
 for name,size,h in profile.archive_records:
  p=regular_file(folder/name);require(p.stat().st_size==size and digest_file(p)==h,'QA archive changed during build')

def load_base(path):
 path=regular_file(path);require(digest_file(path)==BASE_EXPORTER_SHA256,'Original exporter hash changed')
 spec=importlib.util.spec_from_file_location('_reviewed_cf1870_base',path);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
 require(module.PROFILE_MANIFEST_SHA256==BASE_MANIFEST_SHA256 and module.EXPECTED_FILE_COUNT==BASE_FILE_COUNT and module.EXPECTED_HOMEPAGES==1870,'Original base profile mismatch')
 return module

def verify_tree(root,expected):
 root=safe_components(root);require(root.is_dir(),'Missing staged output');seen=set();allowed_dirs={str(PurePosixPath(p).parent)for p in expected}
 for p in list(allowed_dirs):allowed_dirs.update(str(x)for x in PurePosixPath(p).parents)
 for directory,dirs,files in os.walk(root,followlinks=False):
  for name in dirs:
   p=Path(directory)/name;require(not p.is_symlink()and p.relative_to(root).as_posix()in allowed_dirs,'Unexpected/symlink staged directory')
  for name in files:
   p=regular_file(Path(directory)/name);rel=p.relative_to(root).as_posix();require(rel in expected and rel not in seen,'Extra staged file');r=expected[rel];require(p.stat().st_size==r['size']and digest_file(p)==r['sha256'],'Staged file changed');seen.add(rel)
 require(seen==set(expected),'Missing staged files')

def append_qa(staged,expected,verified):
 seen=set()
 for pack in verified:
  with zipfile.ZipFile(pack)as archive:
   for info in archive.infolist():
    name=member_guard(info,expected,seen);target=safe_components(staged/name);require(target.resolve().is_relative_to(staged.resolve())and not target.exists(),'QA overwrite or escape rejected');safe_components(target.parent).mkdir(parents=True,exist_ok=True);safe_components(target)
    with target.open('xb')as out:read_verified_member(archive,info,expected[name],out)
    seen.add(name)
 require(seen==set(expected),'Incomplete QA append')

def run_build(packs_dir,qa_dir,output,base_script=None):
 profile=frozen_profile() # Before any filesystem input or mutation.
 destination=safe_components(output);require(not destination.exists(),'Fresh output required; no existing output writes');require(destination.parent.is_dir(),'Output parent must exist')
 require(destination.name not in {'.git','.github','scripts','cloudflare-packs','qa-20261025'},'Unsafe output name')
 packs=safe_components(packs_dir);qa=safe_components(qa_dir)
 for inp in [packs,qa]:require(not(destination.resolve().is_relative_to(inp.resolve())or inp.resolve().is_relative_to(destination.resolve())),'Output overlaps source inputs')
 qm,qe,verified=validate_qa(qa,profile) # All QA content/metadata passes before base extraction.
 base_path=Path(base_script)if base_script is not None else Path(__file__).with_name('build_cloudflare_1870.py');base=load_base(base_path)
 bp=base.frozen_profile();manifest,homes,flats=base.manifest_file(packs,bp);require(digest(regular_file(packs/'packs.json').read_bytes())==BASE_MANIFEST_SHA256,'Original manifest identity mismatch')
 be={r['path']:r for r in manifest['files']};require(len(be)==BASE_FILE_COUNT and len(homes)==1870 and not set(be)&set(qe),'Base count/QA collision')
 require(not any(p==PREFIX or p.startswith(PREFIX+'/')for p in be),'QA prefix already exists in base')
 combined={**be,**qe};require(len(combined)==COMBINED_FILE_COUNT<=FILE_CAP and manifest['total_bytes']+sum(r['size']for r in qe.values())<=MAX_TOTAL_BYTES,'Combined exact file/byte cap')
 with tempfile.TemporaryDirectory(prefix='.cf1870-qa7-',dir=destination.parent)as temp:
  staged=Path(temp)/'output';base.run_build(packs,staged);verify_tree(staged,be)
  recheck_qa(qa,profile,qm);append_qa(staged,qe,verified);verify_tree(staged,combined)
  base.recheck_inputs(packs,bp,manifest);recheck_qa(qa,profile,qm);require(digest_file(regular_file(base_path))==BASE_EXPORTER_SHA256,'Original exporter changed during build')
  safe_components(destination);require(not destination.exists(),'Output appeared during build; no overwrite');os.rename(staged,destination)
 result={'files':COMBINED_FILE_COUNT,'base_files_preserved':BASE_FILE_COUNT,'qa_files_added':QA_FILE_COUNT,'directory_businesses_unchanged':1870,'qa_previews':7,'base_manifest_sha256':BASE_MANIFEST_SHA256,'qa_manifest_sha256':profile.manifest_sha256,'url_rewrites':0}
 print(json.dumps(result,sort_keys=True));return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packs-dir',default='cloudflare-packs');p.add_argument('--qa-dir',default='qa-20261025');p.add_argument('--output',default='_site');a=p.parse_args()
 try:run_build(a.packs_dir,a.qa_dir,a.output)
 except (ValueError,OSError,zipfile.BadZipFile,UnicodeError)as e:p.exit(1,'Build rejected: '+str(e)+'\n')
if __name__=='__main__':main()
