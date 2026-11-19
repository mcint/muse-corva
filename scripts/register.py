# /// script
# requires-python = ">=3.9"
# ///
"""Register Muse Corva from apps/muse-corva/manifest.json (GitHub manifest flow).

uv run scripts/register.py      then open http://localhost:8765/ and click Create.
Secrets go to the macOS keychain (service "muse-corva") via `security -i` on
stdin, never argv or disk. Non-secret details go to apps/muse-corva/app.json.
"""
import base64, html, http.server, json, os, pathlib, secrets, subprocess, sys
import urllib.parse, urllib.request, webbrowser

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "apps" / "muse-corva"
PORT = int(os.environ.get("MUSE_CORVA_PORT", "8765"))
OWNER = os.environ.get("MUSE_CORVA_OWNER")  # org login; unset = personal account
STATE = secrets.token_urlsafe(16)
HDRS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

manifest = json.loads((APP / "manifest.json").read_text())
manifest["redirect_url"] = f"http://localhost:{PORT}/callback"
target = (f"https://github.com/organizations/{OWNER}/settings/apps/new" if OWNER
          else "https://github.com/settings/apps/new")
FORM = f"""<!doctype html><meta charset=utf-8><title>Register Muse Corva</title>
<body style="font:16px system-ui;max-width:40em;margin:3em auto">
<h1>Register {html.escape(manifest['name'])}</h1>
<p>Sends <code>apps/muse-corva/manifest.json</code> to GitHub. You review and
click <b>Create GitHub App</b> there; GitHub sends you back here.</p>
<pre>{html.escape(json.dumps(manifest['default_permissions'], indent=2))}</pre>
<form action="{target}?state={STATE}" method=post>
<input type=hidden name=manifest value="{html.escape(json.dumps(manifest))}">
<button style="font-size:1.1em">Continue to GitHub</button></form>"""


def keychain(account: str, secret: str) -> None:
    cmd = f"add-generic-password -U -s muse-corva -a {account} -w {secret}\n"
    subprocess.run(["security", "-i"], input=cmd, text=True, check=True,
                   stdout=subprocess.DEVNULL)


def get(url: str, method: str = "GET") -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, method=method, headers=HDRS)) as r:
        return json.load(r)


class Handler(http.server.BaseHTTPRequestHandler):
    def reply(self, body: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/":
            return self.reply(FORM)
        if u.path != "/callback":
            return self.reply("not found", 404)
        if q.get("state", [""])[0] != STATE or "code" not in q:
            return self.reply("state mismatch or missing code; start over at /", 400)
        app = get(f"https://api.github.com/app-manifests/{q['code'][0]}/conversions", "POST")
        keychain("private-key", base64.b64encode(app["pem"].encode()).decode())
        keychain("client-secret", app["client_secret"])
        if app.get("webhook_secret"):
            keychain("webhook-secret", app["webhook_secret"])
        public = {k: app[k] for k in ("id", "slug", "name", "client_id", "node_id", "html_url")}
        public["owner"] = app["owner"]["login"]
        try:
            public["bot_user_id"] = get(f"https://api.github.com/users/{app['slug']}%5Bbot%5D")["id"]
        except Exception as e:  # rare: bot user not visible yet; as-bot needs it for commit email
            print(f"warning: bot user lookup failed ({e}); fill bot_user_id later", file=sys.stderr)
        (APP / "app.json").write_text(json.dumps(public, indent=2) + "\n")
        install = f"{app['html_url']}/installations/new"
        self.reply(f"<p>Registered <b>{html.escape(app['slug'])}</b> (id {app['id']}). "
                   f"Secrets are in keychain service <code>muse-corva</code>.</p>"
                   f"<p>Next: <a href='{install}'>install it on selected repos</a>.</p>")
        print(f"registered {app['slug']} id={app['id']}\nsecrets: keychain service muse-corva\n"
              f"wrote {APP / 'app.json'}\nnext: install at {install}")
        self.server.done = True

    def log_message(self, *a):  # quiet
        pass


if __name__ == "__main__":
    if (APP / "app.json").exists() and "--force" not in sys.argv:
        sys.exit("apps/muse-corva/app.json exists: already registered (pass --force to register again)")
    srv = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    srv.done = False
    url = f"http://localhost:{PORT}/"
    print(f"open {url} and click Continue to GitHub, then Create GitHub App")
    if "--no-open" not in sys.argv:
        webbrowser.open(url)
    while not srv.done:
        srv.handle_request()
