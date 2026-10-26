#!/usr/bin/env python3
"""Offline, dependency-free, fail-closed unpack build for this one Pages site."""
from pathlib import Path, PurePosixPath
import hashlib,json,zipfile,tempfile,shutil,stat

PINNED_MANIFEST_SHA256 = "649520ad5af841514b664bdcdc68b45b4508c1a6d5ba3d7c551c7c7729b0367b"
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"_site"
def require(test,message):
    if not test:raise RuntimeError(message)
def sha(b):return hashlib.sha256(b).hexdigest()
def safe_path(s):
    p=PurePosixPath(s)
    require(bool(s) and not p.is_absolute() and "\\" not in s and not any(x in (".","..","") for x in s.split("/")),"Unsafe path")
    return p
require(not OUT.is_symlink(),"Refusing symlink output")
if OUT.exists():shutil.rmtree(OUT)
raw=(ROOT/"release-manifest.json").read_bytes()
require(sha(raw)==PINNED_MANIFEST_SHA256,"Manifest hash mismatch")
m=json.loads(raw)
require(m["schema"]==1 and m["site"]=="donsbarbershop" and m["origin"]=="https://donsbarbershop.pages.dev" and m["output"]=="_site","Wrong site manifest")
expected={r["path"]:r for r in m["files"]}
require(len(expected)==len(m["files"]) and len(expected)<1000,"Duplicate/excessive manifest paths")
require(sum(r["bytes"] for r in expected.values())<30*1024*1024,"Excessive payload")
for name in expected:safe_path(name)
archives={r["path"]:r for r in m["archives"]}
require(len(archives)==len(m["archives"]),"Duplicate archive")
require(set(p.name for p in ROOT.glob("site-*.zip"))==set(archives),"Missing/unexpected archive")
seen=set()
with tempfile.TemporaryDirectory(prefix=".unpack-",dir=ROOT) as temp:
    staging=Path(temp)
    for name,a in archives.items():
        require(safe_path(name).parent==PurePosixPath("."),"Nested archive rejected")
        path=ROOT/name;require(not path.is_symlink(),"Archive symlink rejected")
        raw=path.read_bytes();require(len(raw)==a["bytes"] and sha(raw)==a["sha256"],"Archive hash mismatch: "+name)
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                rel=info.filename;safe_path(rel)
                require(not info.is_dir() and not stat.S_ISLNK(info.external_attr>>16),"Directory/link archive member rejected")
                require(rel in expected and rel not in seen,"Unexpected/duplicate archive member: "+rel)
                r=expected[rel];require(r["archive"]==name and info.file_size==r["bytes"],"Member mismatch: "+rel)
                data=z.read(info);require(len(data)==r["bytes"] and sha(data)==r["sha256"],"File hash mismatch: "+rel)
                dest=staging/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);seen.add(rel)
    require(seen==set(expected),"Missing files")
    require((staging/"index.html").is_file(),"Missing homepage")
    for rel,r in expected.items():require(sha((staging/rel).read_bytes())==r["sha256"],"Extracted hash mismatch")
    staging.rename(OUT)
print("Verified",len(seen),"files -> _site for https://donsbarbershop.pages.dev/")
