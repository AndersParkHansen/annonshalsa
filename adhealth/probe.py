"""Bounded, anonymous Chromium observation of one page."""
import ipaddress
import os
import re
import shutil
import socket
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import getproxies, proxy_bypass

from playwright.sync_api import Error as BrowserError

from .model import DEVICES, ROOT

FIXTURE_URL = "https://faltjournalen.example/artikel/en-morgon-vid-vattnet"
OBSERVE = (ROOT / "adhealth/observe.js").read_text()
DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
STEPS = 16


def hostname(value):
    host = value.lower().encode("idna").decode("ascii")
    if len(host) > 253 or "." not in host or not all(DNS_LABEL.fullmatch(s) for s in host.split(".")):
        raise ValueError("Ange ett fullständigt publikt domännamn.")
    return host


def public_url(value):
    u = urlsplit(value)
    if (u.scheme != "https" or u.username is not None or u.password is not None or
            not u.hostname or u.port not in (None, 443) or "\\" in value or any(c.isspace() for c in value)):
        raise ValueError("Ange en HTTPS-adress utan inloggningsuppgifter och med standardport.")
    return hostname(u.hostname)


def resolve_hosts(hosts):
    mappings = []
    for host in sorted(hosts):
        ips = [ipaddress.ip_address(a[4][0]) for a in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)]
        if not ips or any(not ip.is_global or ip.is_multicast for ip in ips):
            raise ValueError(f"{host} saknar en tillåten publik adress.")
        ip = next((i for i in ips if i.version == 4), ips[0])
        mappings.append(f"MAP {host} {ip if ip.version == 4 else '[' + str(ip) + ']'}")
    return mappings


def launch(pw, mappings, target=None):
    exe = os.environ.get("ADHEALTH_CHROMIUM")
    if not exe and not os.path.exists(pw.chromium.executable_path):
        exe = shutil.which("chromium") or shutil.which("google-chrome")
    args = ["--disable-quic", "--disable-background-networking",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp"]
    proxy = None
    resolver = [*mappings, "MAP * ~NOTFOUND"]
    proxy_url = getproxies().get("https") if target and not proxy_bypass(target) else None
    if proxy_url:
        upstream = urlsplit(proxy_url)
        if upstream.scheme not in ("http", "https") or not upstream.hostname:
            raise ValueError("HTTPS_PROXY måste ange en HTTP- eller HTTPS-proxy.")
        server = f"{upstream.scheme}://{upstream.hostname}"
        if upstream.port:
            server += f":{upstream.port}"
        proxy = {"server": server}
        if upstream.username:
            proxy.update(username=unquote(upstream.username), password=unquote(upstream.password or ""))
        resolver.insert(0, "EXCLUDE " + upstream.hostname)
    else:
        args.append("--no-proxy-server")
    args.append("--host-resolver-rules=" + ", ".join(resolver))
    return pw.chromium.launch(executable_path=exe, args=args, proxy=proxy)


def observe(browser, url, device, profile, hosts, fixture=None):
    w, h = DEVICES[device]
    mobile = device == "mobile"
    options = {"viewport": {"width": w, "height": h}, "is_mobile": mobile, "has_touch": mobile,
               "service_workers": "block", "accept_downloads": False}
    if mobile:
        options["user_agent"] = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
                                 "(KHTML, like Gecko) Chrome/" + browser.version + " Mobile Safari/537.36")
    ctx = browser.new_context(**options)
    blocked = set()
    failed = set()
    requests = 0
    # Playwright's HTTP client uses the runtime CA store for managed HTTPS proxies.
    proxy_transport = fixture is None and getproxies().get("https") and not proxy_bypass(urlsplit(url).hostname)
    page = ctx.new_page()
    page.set_default_timeout(8000)

    def route_request(route):
        nonlocal requests
        req = route.request
        if fixture is not None and req.url == FIXTURE_URL and req.resource_type == "document":
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=fixture)
            return
        parsed = urlsplit(req.url)
        requests += 1
        if (fixture is not None or req.method not in ("GET", "HEAD") or parsed.scheme != "https"
                or parsed.hostname not in hosts or parsed.port not in (None, 443) or requests > 250):
            blocked.add(parsed.hostname or "annan")
            route.abort()
        elif proxy_transport:
            try:
                upstream = route.fetch(max_redirects=0, timeout=12000)
            except BrowserError:
                failed.add(req.resource_type)
                route.abort()
                return
            try:
                location = upstream.headers.get("location")
                if location and 300 <= upstream.status < 400:
                    dest = urlsplit(urljoin(req.url, location))
                    if dest.scheme != "https" or dest.hostname not in hosts or dest.port not in (None, 443):
                        blocked.add(dest.hostname or "annan")
                        route.abort()
                        return
                route.fulfill(response=upstream)
            finally:
                upstream.dispose()
        else:
            route.continue_()

    ctx.route("**/*", route_request)
    ctx.route_web_socket("**/*", lambda ws: ws.close())
    page.on("requestfailed", lambda req: failed.add(req.resource_type) if req.resource_type in
            {"script", "image", "document", "xhr", "fetch", "stylesheet", "media"} else None)
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
        if response is None or not response.ok:
            return {"problem": "Ingen läsbar sida. " + (f"HTTP {response.status}." if response else "Svar saknas.")}
        if "html" not in response.headers.get("content-type", "").lower():
            return {"problem": "Svaret innehöll ingen HTML."}
        for target in profile["placements"]:
            if not page.evaluate("""s => {try {document.querySelector(s); return true} catch {return false}}""", target["selector"]):
                raise ValueError(f"Ogiltig CSS-selektor för {target['name']}.")
        page.wait_for_timeout(600)
        data = page.evaluate(OBSERVE, {"targets": profile["placements"], "initial": True})
        steps = 0
        while not data["bottom"] and steps < STEPS:
            page.evaluate("() => window.scrollBy({top:Math.round(innerHeight * .8),behavior:'instant'})")
            steps += 1
            page.wait_for_timeout(220)
            data = page.evaluate(OBSERVE, {"targets": profile["placements"], "initial": False})
        page.wait_for_timeout(500)
        data = page.evaluate(OBSERVE, {"targets": profile["placements"], "initial": False})
        return {"http": response.status, "steps": steps, "slots": data["slots"],
                "blockedHosts": sorted(blocked)[:30], "failedTypes": sorted(failed), "bottom": data["bottom"],
                "partial": bool(blocked or failed or data["capped"] or not data["bottom"])}
    except BrowserError as exc:
        message = str(exc)
        code = re.search(r"net::ERR_[A-Z_]+", message)
        return {"problem": "Webbläsaren kunde inte slutföra läsningen" +
                (f" ({code.group()})." if code else " inom mätfönstret.")}
    finally:
        ctx.close()
