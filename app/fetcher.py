"""Download a web page safely and extract readable text.

User-supplied URLs are risky (server-side request forgery, huge files, slow servers),
so every request is validated and limited.
"""
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ALLOWED_SCHEMES = {"http", "https"}
TIMEOUT_SECONDS = 10
MAX_BYTES = 1_000_000  # 1 MB
MAX_REDIRECTS = 3
USER_AGENT = "RiskSummarizer/1.0"


class FetchError(Exception):
    """Raised when a URL cannot be fetched safely."""


def _is_public_ip(ip_text: str) -> bool:
    ip = ipaddress.ip_address(ip_text.split("%")[0])
    return ip.is_global and not ip.is_multicast


def validate_url(url: str) -> str:
    """Allow only http(s) URLs whose host resolves to public IP addresses."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise FetchError("Only http and https URLs are allowed.")
    host = parsed.hostname
    if not host:
        raise FetchError("The URL has no host name.")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise FetchError("Could not resolve the host name.")

    for info in infos:
        if not _is_public_ip(info[4][0]):
            raise FetchError("URLs that point to private or internal addresses are not allowed.")
    return url.strip()


def extract_text(html: str) -> str:
    """Return the readable text of an HTML page, preferring paragraph text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    text = " ".join(p for p in paragraphs if p)
    if not text:
        text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _read_limited(response: requests.Response) -> bytes:
    chunks, total = [], 0
    for chunk in response.iter_content(chunk_size=8192):
        total += len(chunk)
        if total > MAX_BYTES:
            raise FetchError("The page is too large (limit is 1 MB).")
        chunks.append(chunk)
    return b"".join(chunks)


def _decode(raw: bytes, encoding: str | None) -> str:
    try:
        return raw.decode(encoding or "utf-8", errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def fetch_text(url: str) -> str:
    """Fetch a page and return its text. Redirects are followed manually and re-validated."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        validate_url(current)
        try:
            response = requests.get(
                current,
                timeout=TIMEOUT_SECONDS,
                stream=True,
                allow_redirects=False,
                headers={"User-Agent": USER_AGENT},
            )
        except requests.RequestException:
            raise FetchError("Could not download the page.")

        with response:
            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    raise FetchError("The server sent an invalid redirect.")
                current = urljoin(current, location)
                continue

            if response.status_code >= 400:
                raise FetchError(f"The page returned HTTP {response.status_code}.")

            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                raise FetchError("Only HTML or plain-text pages are supported.")

            body = _decode(_read_limited(response), response.encoding)
            return body if "text/plain" in content_type else extract_text(body)

    raise FetchError("Too many redirects.")
