import socket

import pytest

from app import fetcher
from app.fetcher import FetchError, extract_text, validate_url


def _fake_resolver(ip):
    def fake(host, port, proto=0):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
    return fake


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "http://127.0.0.1/admin",
        "http://localhost:8000/",
        "http://10.0.0.5/",
        "http://192.168.1.10/",
        "http://169.254.169.254/latest/meta-data/",
        "http:///no-host",
    ],
)
def test_rejects_unsafe_urls(url):
    with pytest.raises(FetchError):
        validate_url(url)


def test_accepts_public_address(monkeypatch):
    monkeypatch.setattr(fetcher.socket, "getaddrinfo", _fake_resolver("93.184.216.34"))
    assert validate_url("https://example.com/page") == "https://example.com/page"


def test_rejects_host_that_resolves_to_private_ip(monkeypatch):
    monkeypatch.setattr(fetcher.socket, "getaddrinfo", _fake_resolver("10.1.2.3"))
    with pytest.raises(FetchError):
        validate_url("https://looks-public.example.com/")


def test_extract_text_prefers_paragraphs_and_drops_scripts():
    html = "<html><script>var x=1;</script><body><p>Hello   world.</p><p>Second one.</p></body></html>"
    assert extract_text(html) == "Hello world. Second one."


def test_extract_text_falls_back_to_page_text():
    assert extract_text("<html><body><div>Only a div</div></body></html>") == "Only a div"
