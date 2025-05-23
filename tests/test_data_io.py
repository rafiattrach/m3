import requests

from m3.data_io import COMMON_USER_AGENT, _scrape_urls_from_html_page


class DummyResponse:
    def __init__(self, content, status_code=200, headers=None):
        self.content = content.encode()
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise requests.exceptions.HTTPError(response=self)

    @property
    def reason(self):
        return "Error"

    def iter_content(self, chunk_size=1):
        yield from self.content


def test_scrape_urls(monkeypatch):
    html = (
        "<html><body>"
        '<a href="file1.csv.gz">ok</a>'
        '<a href="skip.txt">no</a>'
        "</body></html>"
    )
    dummy = DummyResponse(html)
    session = requests.Session()
    monkeypatch.setattr(session, "get", lambda url, timeout=None: dummy)
    urls = _scrape_urls_from_html_page("http://example.com/", session)
    assert urls == ["http://example.com/file1.csv.gz"]


def test_scrape_no_matching_suffix(monkeypatch):
    html = '<html><body><a href="file1.txt">ok</a></body></html>'
    dummy = DummyResponse(html)
    session = requests.Session()
    monkeypatch.setattr(session, "get", lambda url, timeout=None: dummy)
    urls = _scrape_urls_from_html_page("http://example.com/", session)
    assert urls == []


def test_common_user_agent_header():
    # Ensure the constant is set and looks like a UA string
    assert isinstance(COMMON_USER_AGENT, str)
    assert "Mozilla/" in COMMON_USER_AGENT
