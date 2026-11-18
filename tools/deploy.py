"""Upload dist/akce to kuponmat.cz (WEDOS FTPS) — only changed files, then remove files that disappeared.

    python -m tools.deploy [--dist dist] [--dry]

Credentials from env: FTP_HOST, FTP_USER, FTP_PASSWORD (GitHub secrets), optional FTP_PORT, FTP_ROOT (web root,
default /domains/kuponmat.cz = the shared WEDOS hosting the site really runs on), FTP_TLS=1 for FTPS.
A manifest (path -> sha1) is kept on the server in /akce/.manifest.json, so a run only sends what changed.
Afterwards prints the changed page URLs (for the Cloudflare purge / IndexNow steps) into dist/changed-urls.txt.
"""
import argparse
import ftplib
import hashlib
import io
import json
import os
import ssl
import sys
from pathlib import Path

REMOTE = os.environ.get("FTP_ROOT", "/domains/kuponmat.cz").rstrip("/") + "/akce"
SITE = "https://kuponmat.cz"


class FTPS(ftplib.FTP_TLS):
    """WEDOS requires TLS session reuse on the data channel."""

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session)
        return conn, size


def connect():
    if os.environ.get("FTP_TLS", "0") != "1":
        f = ftplib.FTP(timeout=90)
        f.connect(os.environ["FTP_HOST"], int(os.environ.get("FTP_PORT") or 21))
        f.login(os.environ["FTP_USER"], os.environ["FTP_PASSWORD"])
        return f
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    f = FTPS(context=ctx)
    f.connect(os.environ["FTP_HOST"], int(os.environ.get("FTP_PORT") or 21), timeout=90)
    f.login(os.environ["FTP_USER"], os.environ["FTP_PASSWORD"])
    f.prot_p()
    return f


def sha(p: Path):
    return hashlib.sha1(p.read_bytes()).hexdigest()


def ensure_dir(f, d, made):
    parts = d.strip("/").split("/")
    cur = ""
    for part in parts:
        cur += "/" + part
        if cur in made:
            continue
        try:
            f.mkd(cur)
            f.sendcmd(f"SITE CHMOD 755 {cur}")   # WEDOS creates 750 -> Apache 403
        except ftplib.error_perm:
            pass
        made.add(cur)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    root = Path(a.dist) / "akce"
    local = {str(p.relative_to(root)): sha(p) for p in root.rglob("*") if p.is_file()}
    f = connect()
    old = {}
    try:
        buf = io.BytesIO()
        f.retrbinary(f"RETR {REMOTE}/.manifest.json", buf.write)
        old = json.loads(buf.getvalue() or b"{}")
    except ftplib.error_perm:
        pass
    changed = [k for k, v in local.items() if old.get(k) != v]
    removed = [k for k in old if k not in local]
    # index.html files and data first-time: upload html last so pages never point to missing images
    # assets first, then the hub index (the /akce/ directory must never be without it), then the other pages
    changed.sort(key=lambda k: (k.endswith(".html"), k != "index.html", k))
    print(f"{len(local)} files, {len(changed)} changed, {len(removed)} removed", file=sys.stderr)
    if a.dry:
        return
    made = set()
    for k in changed:   # directories first, on the main connection
        ensure_dir(f, f"{REMOTE}/{Path(k).parent}" if str(Path(k).parent) != "." else REMOTE, made)

    import threading
    from concurrent.futures import ThreadPoolExecutor
    local_conn = threading.local()
    done = dict(old)          # manifest of what is really on the server (saved every 300 files -> a killed run resumes)
    lock = threading.Lock()
    counter = [0]

    def put(k):
        c = getattr(local_conn, "c", None)
        if c is None:
            c = local_conn.c = connect()
        for attempt in range(3):
            try:
                with open(root / k, "rb") as fh:
                    c.storbinary(f"STOR {REMOTE}/{k}", fh)
                if k not in old:   # new file: WEDOS creates 640 -> Apache 403; an overwritten file keeps its 644
                    c.sendcmd(f"SITE CHMOD 644 {REMOTE}/{k}")
                break
            except (ftplib.all_errors) as e:
                if attempt == 2:
                    raise
                try:
                    c.close()
                except Exception:
                    pass
                c = local_conn.c = connect()
        with lock:
            done[k] = local[k]
            counter[0] += 1
            if counter[0] % 300 == 0:
                print(f"  {counter[0]}/{len(changed)}", file=sys.stderr)
                try:
                    c.storbinary(f"STOR {REMOTE}/.manifest.json", io.BytesIO(json.dumps(done).encode()))
                except ftplib.all_errors:
                    pass

    assets = [k for k in changed if not k.endswith(".html")]
    hub = [k for k in changed if k == "index.html"]
    pages = [k for k in changed if k.endswith(".html") and k != "index.html"]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(put, assets))
    for k in hub:   # the /akce/ directory must never be without its index
        put(k)
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(put, pages))
    try:
        f.voidcmd("NOOP")
    except ftplib.all_errors:   # the main connection idled out during the parallel upload
        f = connect()
    for k in removed:
        try:
            f.delete(f"{REMOTE}/{k}")
        except ftplib.error_perm:
            pass
    f.storbinary(f"STOR {REMOTE}/.manifest.json", io.BytesIO(json.dumps(local).encode()))
    f.sendcmd(f"SITE CHMOD 600 {REMOTE}/.manifest.json")
    f.quit()
    urls = sorted({SITE + "/akce/" + (str(Path(k).parent) + "/" if str(Path(k).parent) != "." else "")
                   for k in changed + removed if k.endswith("index.html")})
    Path(a.dist, "changed-urls.txt").write_text("\n".join(urls))
    print(f"uploaded {len(changed)}, deleted {len(removed)}, changed pages {len(urls)}", file=sys.stderr)


if __name__ == "__main__":
    main()
