#!/usr/bin/env python3
"""Build a host-neutral static mirror of the reviewed exact-270 pack profile.
Standard library only. No network, deploy command, hostname invention, or source edits.
"""
from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import argparse, collections, hashlib, html, json, os, posixpath, re, shutil, stat, tempfile, types

PROFILE_COMMIT = '1ba5e1a2860a6dbb75dbcff4888e31d51c2df0c0'
PROFILE_MANIFEST_SHA256 = '7d7aa3c146dcc00623d8156df6a78836c08e177f9eef61734dfdddc0eabdd78d'
PROFILE_WORKFLOW_SHA256 = '81a2b70c7448e64c787e0771176ad8b344fea52f061a18084f37ced74fa5d9cc'
SOURCE_BASE = '/amhsite-previews/'
CLOUDFLARE_FREE_FILE_CAP = 20_000
TEXT_EXTENSIONS = {'.html', '.css', '.js', '.svg', '.webmanifest', '.txt'}
VALIDATOR_SHA256 = '5f35966be7eb3d34f684a04563e82b9a65918f7df33139cfbcc325c1785b9620'
VALIDATOR_SOURCE = '"""Restrictive policy shared by the local packer and the deployment validator."""\nimport re\nfrom pathlib import PurePosixPath\n\nEXTENSIONS = {\'.html\', \'.css\', \'.js\', \'.svg\', \'.png\', \'.jpg\', \'.jpeg\', \'.webp\', \'.ico\', \'.ttf\', \'.woff\', \'.woff2\', \'.webmanifest\', \'.mp4\'}\nROOT_FILES = {\'index.html\', \'404.html\', \'robots.txt\', \'.nojekyll\'}\nSITE_FILES = {\'index.html\', \'404.html\', \'favicon.ico\', \'robots.txt\', \'site.webmanifest\', \'sw.js\'}\nSUBPAGES = {\'faq\', \'menu\', \'privacy\', \'terms\'}\nBAD_COMPONENTS = {\'node_modules\', \'private\', \'credentials\', \'secrets\', \'src\', \'source\', \'qa\', \'leads\', \'__pycache__\'}\nAPPROVED_MP4 = {\n \'f669f1e75c7498e69cacac58bcff156cd2419e3d51e1d6108bf5c4d8d5a187eb\',\n \'63c28b0b833d8b4b99d6ef1e02dfeb34d6c5acd3745d9e993c6bf84ec86ebcda\',\n \'5df38d6223b0b5d6851b433ab71e27a2fb79005b4932b7bfb9850171f563b608\',\n \'a96d6031e9af134fae64ec65921fdb9a832746dbf50cd4940232f6f65af6c752\',\n \'f6903f735fb8a2223ab800f786572c22ca3709410c2ba8584f4b2142a74ba410\',\n \'7c15b8aaac6a299db4c536a5881d4c0a3a93fa6f21633abd2dca507112e24345\',\n \'7cc6598e5c43c74443264fbde8a524c8c62760f3ce45e91460fce7a9526f8546\',\n \'c3b838769cc93dc8f2f57f57bfe7e898985f3c9e722a3241b11ae804afde1ddc\',\n \'26a8e7e00bec5499f17b38ba50dd88ace06e7f5bb0b0b238a79758da368437e0\',\n \'0acf5959ba6219f3e9c8782db180fc831837f8a0dbe0c202341a670b26c71582\',\n \'017ebb76ae5a4dfbf932cfb864553bc8c74cbea4f91f2b0f830511f5a17df015\',\n\n \'c8d48e1e03b9b812ab9e3faaccdcb9c3cb4b4ae8129d17d3f2dfa83b0b8d53d7\',\n \'5638aef456dee6808d134d167900bdc0f4b5cb531e9a28713be3815756345a37\',\n \'f514d51c243cbee88eff16422c48a7484a3a08ac3a3f5033c9f7a59f1d91f605\',\n}\nMAX_MP4_BYTES = 2_000_000\n# Exact current live enhanced dye asset; no generic size-cap expansion.\nAPPROVED_MP4_SIZE_EXCEPTIONS = {\'c3b838769cc93dc8f2f57f57bfe7e898985f3c9e722a3241b11ae804afde1ddc\': 6_000_000}\nMAX_TOTAL_BYTES = 900_000_000\nMAX_FILE_BYTES = 10_000_000\nMAX_FILES = 30000\nMAX_PACK_BYTES = 25 * 1024 * 1024\n\ndef allowed_path(name):\n    if not isinstance(name, str) or not name or len(name) > 240:\n        return False\n    if \'\\\\\' in name or \'\\x00\' in name or name.startswith(\'/\') or name.endswith(\'/\'):\n        return False\n    p = PurePosixPath(name)\n    if p.as_posix() != name or any(x in {\'\', \'.\', \'..\'} for x in name.split(\'/\')):\n        return False\n    if name in ROOT_FILES:\n        return True\n    if not re.fullmatch(r\'[A-Za-z0-9_./-]+\', name):\n        return False\n    if any(x.startswith(\'.\') or x.lower() in BAD_COMPONENTS for x in p.parts):\n        return False\n    if p.suffix.lower() not in EXTENSIONS and p.name != \'robots.txt\':\n        return False\n    if p.suffix.lower() == \'.mp4\':\n        return len(p.parts) == 2 and p.parts[0] == \'assets\' and p.suffix == \'.mp4\' and p.stem in APPROVED_MP4\n    if p.parts[0] == \'assets\':\n        return len(p.parts) == 2 and bool(re.fullmatch(r\'[0-9a-f]{40,64}\\.[a-z0-9]+\', p.name)) and p.suffix.lower() in EXTENSIONS\n    if len(p.parts) < 3 or p.parts[0] not in {\'barbers\', \'restaurants\'}:\n        return False\n    if not re.fullmatch(r\'[a-z0-9][a-z0-9-]{0,119}\', p.parts[1]):\n        return False\n    tail = p.parts[2:]\n    if len(tail) == 1:\n        return tail[0] in SITE_FILES\n    if len(tail) == 2 and tail[0] in SUBPAGES and tail[1] == \'index.html\':\n        return True\n    if tail[0] == \'assets\':\n        return len(tail) >= 2 and p.suffix.lower() in EXTENSIONS\n    return False\n\n"""Validate the exact public pack manifest, then extract static files safely."""\nimport argparse, hashlib, json, re, shutil, stat, zipfile\nfrom pathlib import Path\n\n\ndef strict_object(pairs):\n    result={}\n    for key,value in pairs:\n        if key in result: raise ValueError(\'Duplicate JSON key\')\n        result[key]=value\n    return result\n\ndef integer(n):\n    return type(n) is int and n >= 0\n\ndef sha(s):\n    return isinstance(s,str) and bool(re.fullmatch(r\'[0-9a-f]{64}\',s))\n\ndef digest_file(path):\n    with path.open(\'rb\') as f:\n        return hashlib.file_digest(f,\'sha256\').hexdigest()\n\ndef extract(pack_dir, destination):\n    pack_dir=Path(pack_dir).resolve(strict=True)\n    destination=Path(destination).absolute()\n    if destination.exists() or destination.is_symlink():\n        raise ValueError(\'Extraction destination must not exist\')\n    mf=pack_dir/\'packs.json\'\n    if mf.is_symlink() or not mf.is_file() or mf.stat().st_size > 16_000_000:\n        raise ValueError(\'Invalid manifest file\')\n    manifest=json.loads(mf.read_text(),object_pairs_hook=strict_object)\n    if set(manifest)!={\'format\',\'file_count\',\'total_bytes\',\'packs\',\'files\'} or manifest[\'format\']!=1:\n        raise ValueError(\'Invalid manifest schema\')\n    if not integer(manifest[\'file_count\']) or not 0<manifest[\'file_count\']<=MAX_FILES:\n        raise ValueError(\'Invalid static file count\')\n    if not integer(manifest[\'total_bytes\']) or manifest[\'total_bytes\']>MAX_TOTAL_BYTES:\n        raise ValueError(\'Published site exceeds size policy\')\n    if not isinstance(manifest[\'files\'],list) or len(manifest[\'files\'])!=manifest[\'file_count\']:\n        raise ValueError(\'Invalid static file list\')\n    expected={}\n    for r in manifest[\'files\']:\n        if not isinstance(r,dict) or set(r)!={\'path\',\'sha256\',\'size\'}:\n            raise ValueError(\'Invalid static record\')\n        if not allowed_path(r[\'path\']) or r[\'path\'] in expected:\n            raise ValueError(\'Unsafe or duplicate static path\')\n        if not integer(r[\'size\']) or r[\'size\']>MAX_FILE_BYTES or not sha(r[\'sha256\']):\n            raise ValueError(\'Invalid static size/hash\')\n        expected[r[\'path\']]=r\n    if sum(r[\'size\'] for r in expected.values())!=manifest[\'total_bytes\']:\n        raise ValueError(\'Uncompressed size mismatch\')\n    if not ROOT_FILES<=expected.keys():\n        raise ValueError(\'Required root files missing\')\n    if len([p for p in expected if p.count(\'/\')==2 and p.endswith(\'/index.html\')])!=270:\n        raise ValueError(\'Expected exactly 270 homepages\')\n    if not isinstance(manifest[\'packs\'],list) or not 1<=len(manifest[\'packs\'])<=20:\n        raise ValueError(\'Invalid pack count\')\n    pack_names=set(); verified=[]; seen=set()\n    for pack in manifest[\'packs\']:\n        if not isinstance(pack,dict) or set(pack)!={\'name\',\'size\',\'sha256\'}:\n            raise ValueError(\'Invalid pack record\')\n        name=pack[\'name\']\n        if not isinstance(name,str) or not re.fullmatch(r\'part-[0-9]{3}\\.zip\',name) or name in pack_names:\n            raise ValueError(\'Invalid or duplicate pack filename\')\n        if not integer(pack[\'size\']) or not 0<pack[\'size\']<MAX_PACK_BYTES or not sha(pack[\'sha256\']):\n            raise ValueError(\'Invalid pack size/hash\')\n        pack_names.add(name); path=pack_dir/name\n        if path.is_symlink() or not path.is_file() or path.stat().st_size!=pack[\'size\']:\n            raise ValueError(\'Pack absent or wrong size\')\n        if digest_file(path)!=pack[\'sha256\']:\n            raise ValueError(\'Pack integrity mismatch\')\n        with zipfile.ZipFile(path) as archive:\n            for info in archive.infolist():\n                mode=info.external_attr>>16\n                if info.is_dir() or not stat.S_ISREG(mode) or info.flag_bits&1:\n                    raise ValueError(\'Directory, symlink, special, or encrypted entry rejected\')\n                if info.compress_type not in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED}:\n                    raise ValueError(\'Unsupported archive compression\')\n                if info.filename in seen or not allowed_path(info.filename) or info.filename not in expected:\n                    raise ValueError(\'Duplicate, unsafe, or unexpected archive path\')\n                record=expected[info.filename]\n                if info.file_size!=record[\'size\'] or info.file_size>MAX_FILE_BYTES:\n                    raise ValueError(\'Archive entry size mismatch\')\n                with archive.open(info) as stream:\n                    h=hashlib.sha256(); size=0\n                    while chunk:=stream.read(1024*1024):\n                        size+=len(chunk)\n                        if size>record[\'size\']: raise ValueError(\'Archive entry expansion exceeds manifest\')\n                        h.update(chunk)\n                if size!=record[\'size\'] or h.hexdigest()!=record[\'sha256\']:\n                    raise ValueError(\'Static content integrity mismatch\')\n                if info.filename.lower().endswith(\'.mp4\'):\n                    if record[\'sha256\'] not in APPROVED_MP4 or Path(info.filename).stem != record[\'sha256\'] or size > APPROVED_MP4_SIZE_EXCEPTIONS.get(record[\'sha256\'], MAX_MP4_BYTES):\n                        raise ValueError(\'Unapproved or oversized MP4\')\n                    with archive.open(info) as stream:\n                        header = stream.read(32)\n                    if header[4:8] != b\'ftyp\' or header[8:12] != b\'isom\' or b\'avc1\' not in header:\n                        raise ValueError(\'MP4 MIME/codec signature mismatch\')\n                seen.add(info.filename)\n        verified.append(path)\n    if seen!=set(expected):\n        raise ValueError(\'Static files missing from packs\')\n    if {p.name for p in pack_dir.glob(\'part-*.zip\')}!=pack_names:\n        raise ValueError(\'Unexpected ZIP packs present\')\n    # Every path, type, count, length and digest has now passed before writes begin.\n    destination.mkdir(parents=True,exist_ok=False)\n    try:\n        for path in verified:\n            with zipfile.ZipFile(path) as archive:\n                for info in archive.infolist():\n                    target=destination/info.filename\n                    target.parent.mkdir(parents=True,exist_ok=True)\n                    with archive.open(info) as src, target.open(\'xb\') as dst:\n                        shutil.copyfileobj(src,dst,1024*1024)\n                    if digest_file(target)!=expected[info.filename][\'sha256\']:\n                        raise ValueError(\'Post-extraction integrity mismatch\')\n        for name in [\'index.html\']+[p for p in expected if p.count(\'/\')==2 and p.endswith(\'/index.html\')]:\n            if \'noindex\' not in (destination/name).read_text().lower():\n                raise ValueError(\'Preview homepage lacks noindex\')\n        if \'Disallow: /\' not in (destination/\'robots.txt\').read_text():\n            raise ValueError(\'Root robots exclusion missing\')\n    except Exception:\n        shutil.rmtree(destination)\n        raise\n    print(f\'Validated {len(expected)} static files ({manifest["total_bytes"]:,} bytes) in {len(verified)} packs.\')\n\nif __name__==\'__main__\':\n    parser=argparse.ArgumentParser()\n    parser.add_argument(\'pack_dir\',nargs=\'?\',default=\'packs\')\n    parser.add_argument(\'destination\',nargs=\'?\',default=\'_site\')\n    args=parser.parse_args()\n    extract(args.pack_dir,args.destination)\n'

def digest(data):return hashlib.sha256(data).hexdigest()
def git_blob(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def validator():
    if digest(VALIDATOR_SOURCE.encode())!=VALIDATOR_SHA256:raise ValueError('Embedded reviewed validator integrity mismatch')
    ns={'__name__':'reviewed_pack_validator'};exec(compile(VALIDATOR_SOURCE,'reviewed_pack_validator','exec'),ns)
    return types.SimpleNamespace(**ns)

ATTR=re.compile(r'(?P<name>[A-Za-z_:][A-Za-z0-9_:.-]*)(?P<eq>\s*=\s*)(?P<q>[\"\'])(?P<value>.*?)(?P=q)',re.S)
CSS_URL=re.compile(r'url\(\s*(?P<q>[\"\']?)(?P<value>.*?)(?P=q)\s*\)',re.I)
CSS_IMPORT=re.compile(r'(?P<head>@import\s+)(?P<q>[\"\'])(?P<value>.*?)(?P=q)',re.I)
SW_REGISTER=re.compile(r'(?P<head>\b(?:navigator\.)?serviceWorker\s*\.\s*register\s*\(\s*)(?P<q>[\"\'])(?P<value>[^\"\']*)(?P=q)')
MANIFEST_FIELD=re.compile(r'(?P<head>\"(?P<key>id|scope|start_url|src)\"\s*:\s*)(?P<string>\"(?:\\.|[^\"\\])*\")')
EXTERNAL_URL=re.compile(r'https?://[^\s\"\'<>]+')
URL_ATTRS={'href','src','poster','action','data-src'}
META_URL_FIELDS={'og:url','og:image','twitter:url','twitter:image'}


def internal_ref(value,source,base):
    u=urlsplit(value)
    if not value or value.startswith('#') or u.scheme or u.netloc:return None
    path=unquote(u.path)
    if path.startswith('/'):
        if base!='/' and not path.startswith(base):raise ValueError('Root-relative URL outside selected base: '+value)
        path=path[len(base):] if base!='/' else path[1:]
    else:path=posixpath.normpath(posixpath.join(posixpath.dirname(source),path))
    path=path.rstrip('/')
    if path in {'','.'}:path='index.html'
    if path.startswith('/') or path=='..' or path.startswith('../') or '\\' in path:raise ValueError('Reference escapes output root')
    return path


def css_transform(text,callback):
    def url(m):
        old=m['value'];new=callback(old)
        return m.group(0) if new==old else 'url('+m['q']+new+m['q']+')'
    def imp(m):
        old=m['value'];new=callback(old)
        return m.group(0) if new==old else m['head']+m['q']+new+m['q']
    return CSS_IMPORT.sub(imp,CSS_URL.sub(url,text))


def js_transform(text,callback):
    def replace(m):
        old=m['value'];new=callback(old)
        return m.group(0) if old==new else m['head']+m['q']+new+m['q']
    result=SW_REGISTER.sub(replace,text)
    # This reviewed profile has only these JS-local prefix uses. Never rewrite arbitrary code strings.
    remaining=SW_REGISTER.sub('',result)
    if re.search(r'[\"\']'+re.escape(SOURCE_BASE),remaining):raise ValueError('Unreviewed JavaScript project-prefix field')
    return result


class HTMLURLs(HTMLParser):
    def __init__(self,text,callback):
        super().__init__(convert_charrefs=False);self.raw=text;self.callback=callback;self.edits=[];self.stack=[];self.offsets=[0]+[i+1 for i,c in enumerate(text) if c=='\n'];self.visible=[];self.script_types=[]
    def source_position(self):line,col=self.getpos();return self.offsets[line-1]+col
    def handle_starttag(self,tag,attrs):
        raw=self.get_starttag_text();values=dict(attrs)
        def attr(m):
            key=m['name'].lower();old=html.unescape(m['value']);new=old
            if key in URL_ATTRS:new=self.callback(old)
            elif key=='style':new=css_transform(old,self.callback)
            elif key=='content' and tag=='meta' and values.get('property',values.get('name','')) in META_URL_FIELDS:new=self.callback(old)
            elif key=='srcset':raise ValueError('srcset is absent from this exact reviewed profile; separate adapter review required')
            return m.group(0) if old==new else m['name']+m['eq']+m['q']+html.escape(new,quote=True)+m['q']
        new=ATTR.sub(attr,raw)
        if new!=raw:self.edits.append((self.source_position(),self.source_position()+len(raw),new))
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append(tag)
        if tag=='script':self.script_types.append(values.get('type',''))
    def handle_startendtag(self,tag,attrs):
        count=len(self.stack);self.handle_starttag(tag,attrs);self.stack=self.stack[:count]
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i]==tag:del self.stack[i:];break
        if tag=='script' and self.script_types:self.script_types.pop()
    def handle_data(self,data):
        new=data
        if self.stack and self.stack[-1]=='style':new=css_transform(data,self.callback)
        elif self.stack and self.stack[-1]=='script':
            if self.script_types and 'json' in self.script_types[-1]:
                # Existing absolute canonical/schema identifiers intentionally remain intact.
                if re.search(r'\"'+re.escape(SOURCE_BASE),data):raise ValueError('Unreviewed root-relative structured-data field')
            else:new=js_transform(data,self.callback)
        elif data.strip():self.visible.append(' '.join(data.split()))
        if new!=data:self.edits.append((self.source_position(),self.source_position()+len(data),new))
    def result(self):
        output=self.raw
        for start,end,new in sorted(self.edits,reverse=True):output=output[:start]+new+output[end:]
        return output


def text_transform(path,text,callback):
    ext=Path(path).suffix
    if ext in {'.html','.svg'}:
        parser=HTMLURLs(text,callback);parser.feed(text);return parser.result()
    if ext=='.css':return css_transform(text,callback)
    if ext=='.js':return js_transform(text,callback)
    if ext=='.webmanifest':
        json.loads(text)
        def replace(m):
            old=json.loads(m['string']);new=callback(old)
            return m.group(0) if old==new else m['head']+json.dumps(new,ensure_ascii=False)
        return MANIFEST_FIELD.sub(replace,text)
    return text


class Rebaser:
    def __init__(self,files,base):
        self.files=files;self.base=base;self.mapping={};self.contents={};self.active=set();self.changed_text=[];self.renamed=[];self.url_edits=0
        self.addressed={}
        for path,data in files.items():
            if Path(path).suffix not in TEXT_EXTENSIONS:continue
            stem=Path(path).stem
            if re.fullmatch('[0-9a-f]{64}',stem) and stem==digest(data):self.addressed[path]='sha256'
            elif re.fullmatch('[0-9a-f]{40}',stem) and stem==git_blob(data):self.addressed[path]='gitblob'
    def target(self,path):
        if path in self.addressed:self.render(path)
        return self.mapping.get(path,path)
    def rewrite(self,value,source):
        u=urlsplit(value)
        if not value or value.startswith('#') or u.scheme or u.netloc:return value
        tail=('?'+u.query if u.query else '')+('#'+u.fragment if u.fragment else '')
        if u.path.startswith(SOURCE_BASE):
            original=unquote(u.path[len(SOURCE_BASE):]);trailing=original.endswith('/');lookup=original.rstrip('/') or 'index.html'
            new=self.target(lookup)
            result=self.base+(new if original else '')+('/' if trailing and new and not new.endswith('/') else '')+tail
            # Bare source project root maps to selected base exactly.
            if not original:result=self.base+tail
        else:
            original=internal_ref(value,source,'/')
            if original is None:return value
            new=self.target(original)
            if new==original:return value
            if u.path.startswith('/'):result='/'+new+tail
            else:
                result=posixpath.relpath(new,posixpath.dirname(source) or '.')+tail
                if u.path.startswith('./') and not result.startswith('.'):result='./'+result
        if result!=value:self.url_edits+=1
        return result
    def render(self,path):
        if path in self.contents:return self.contents[path]
        if path in self.active:raise ValueError('Content-addressed dependency cycle: '+path)
        self.active.add(path);old=self.files[path];new=old
        if Path(path).suffix in TEXT_EXTENSIONS:
            original=old.decode();changed=text_transform(path,original,lambda url:self.rewrite(url,path));new=changed.encode()
            if new!=old:
                if collections.Counter(EXTERNAL_URL.findall(original))!=collections.Counter(EXTERNAL_URL.findall(changed)):raise ValueError('Absolute external URLs changed: '+path)
                if path.endswith('.html'):
                    a=HTMLURLs(original,lambda x:x);a.feed(original);b=HTMLURLs(changed,lambda x:x);b.feed(changed)
                    if a.visible!=b.visible:raise ValueError('Visible page copy changed: '+path)
                self.changed_text.append(path)
        target=path
        if path in self.addressed and new!=old:
            h=digest(new) if self.addressed[path]=='sha256' else git_blob(new)
            target=str(PurePosixPath(path).with_name(h+Path(path).suffix));self.renamed.append({'before':path,'after':target})
        self.mapping[path]=target;self.contents[path]=new;self.active.remove(path);return new
    def run(self):
        for path in sorted(self.files):self.render(path)
        output={}
        for path,data in self.contents.items():
            target=self.mapping[path]
            if target in output:raise ValueError('Rebased output path collision')
            output[target]=data
        return output


def check_dependencies(files,base):
    checked=0;absolute=set()
    for path,data in files.items():
        if Path(path).suffix not in TEXT_EXTENSIONS:continue
        text=data.decode()
        def check(value):
            nonlocal checked
            u=urlsplit(value)
            if u.scheme or u.netloc:
                if value.startswith('https://pain2hustle.github.io/amhsite-previews/'):absolute.add(value)
                return value
            target=internal_ref(value,path,base)
            if target is not None:
                if base=='/' and u.path.startswith(SOURCE_BASE):raise ValueError('Unrebased project-prefix dependency: '+path)
                if target not in files and target.rstrip('/')+'/index.html' not in files:raise ValueError('Missing output dependency: '+path+' -> '+value)
                checked+=1
            return value
        text_transform(path,text,check)
    return checked,sorted(absolute)


def run_build(packs_dir,output,base):
    packs=Path(packs_dir)
    if packs.is_symlink():raise ValueError('Symlink pack root rejected')
    packs=packs.resolve(strict=True)
    destination=Path(output).absolute()
    if destination.exists() or destination.is_symlink():raise ValueError('Output must not already exist; no overwrites')
    parent=destination.parent.resolve(strict=True);destination=parent/destination.name
    if destination==packs or destination in packs.parents or packs in destination.parents:raise ValueError('Output overlaps input packs')
    if destination.name in {'.git','.github','packs'}:raise ValueError('Unsafe output directory name')
    if base not in {'/','/amhsite-previews/'}:raise ValueError('Only reviewed root or explicit GitHub base is supported')
    manifest_bytes=(packs/'packs.json').read_bytes()
    if digest(manifest_bytes)!=PROFILE_MANIFEST_SHA256:raise ValueError('Manifest does not match the exact reviewed 270-site profile; another profile requires review')
    manifest=json.loads(manifest_bytes)
    if manifest['file_count']>CLOUDFLARE_FREE_FILE_CAP:raise ValueError('Output would exceed the 20,000-file Free cap; no plan upgrade is performed')
    v=validator()
    with tempfile.TemporaryDirectory(prefix='.cloudflare-build-',dir=parent) as td:
        root=Path(td);validated=root/'validated'
        # Embedded validator verifies EVERY pack/member/hash/type/size/count/path/MP4 before extraction begins.
        v.extract(packs,validated)
        original={r['path']:(validated/r['path']).read_bytes() for r in manifest['files']}
        rebaser=Rebaser(original,base);rebased=rebaser.run()
        if len(rebased)>CLOUDFLARE_FREE_FILE_CAP:raise ValueError('Free static-file cap exceeded')
        if sum(map(len,rebased.values()))>v.MAX_TOTAL_BYTES:raise ValueError('Output exceeds unchanged total-byte limit')
        for path,data in rebased.items():
            if not v.allowed_path(path):raise ValueError('Output violates unchanged static path allowlist')
            if len(data)>v.MAX_FILE_BYTES:raise ValueError('Output exceeds unchanged per-file limit')
        before_mp4={n:b for n,b in original.items() if n.endswith('.mp4')};after_mp4={n:b for n,b in rebased.items() if n.endswith('.mp4')}
        if before_mp4!=after_mp4:raise ValueError('MP4 paths/bytes changed')
        homepaths={n for n in original if n.count('/')==2 and n.endswith('/index.html')}
        if len(homepaths)!=270 or {n for n in rebased if n.count('/')==2 and n.endswith('/index.html')}!=homepaths:raise ValueError('Original exact homepage set changed')
        for path in ['index.html',*homepaths]:
            if 'noindex' not in rebased[path].decode().lower():raise ValueError('Noindex missing after rebase')
        checked,retained=check_dependencies(rebased,base)
        staged=root/'output';staged.mkdir()
        for path,data in sorted(rebased.items()):
            f=staged/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
        # Fail closed before exposing final output if any input changed during the build.
        if digest((packs/'packs.json').read_bytes())!=PROFILE_MANIFEST_SHA256:raise ValueError('Input manifest changed during build')
        for record in manifest['packs']:
            source=packs/record['name']
            if source.is_symlink() or source.stat().st_size!=record['size'] or v.digest_file(source)!=record['sha256']:raise ValueError('Input pack changed during build')
        os.rename(staged,destination)
    retained_count=sum(sum(url.startswith('https://pain2hustle.github.io/amhsite-previews/') for url in EXTERNAL_URL.findall(data.decode())) for path,data in original.items() if Path(path).suffix in TEXT_EXTENSIONS)
    return {'profile_commit':PROFILE_COMMIT,'source_manifest_sha256':PROFILE_MANIFEST_SHA256,'source_workflow_sha256':PROFILE_WORKFLOW_SHA256,'embedded_validator_sha256':VALIDATOR_SHA256,'output':str(destination),'base_path':base,'files':len(rebased),'bytes':sum(map(len,rebased.values())),'homepages':270,'free_file_cap':CLOUDFLARE_FREE_FILE_CAP,'text_files_rebased':len(rebaser.changed_text),'url_fields_rebased':rebaser.url_edits,'content_addressed_dependencies_renamed':rebaser.renamed,'local_dependency_checks':checked,'unchanged_mp4_files':len(before_mp4),'absolute_github_metadata_preserved':True,'retained_absolute_github_url_occurrences':retained_count,'retained_absolute_github_urls_sample':retained[:5],'canonical_or_hostname_invented':False,'source_files_modified':False,'deployment_performed':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packs-dir',default='packs',help='Reviewed source pack directory (default: packs)')
    p.add_argument('--base-path',required=True,choices=['/','/amhsite-previews/'],help='Explicit output URL base: / for Cloudflare Pages root')
    p.add_argument('--output',required=True,help='New output directory, e.g. _site; must not exist')
    args=p.parse_args();report=run_build(args.packs_dir,args.output,args.base_path)
    # No report or provenance is written inside the public static output directory.
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
