from __future__ import annotations

import socket
from datetime import date

import httpx
import pytest

from hifc.ingest import (
    IngestError,
    UnsafeUrlError,
    YoutubeTranscriptUnavailable,
    build_source_from_file,
    build_source_from_html,
    build_source_from_paste,
    build_source_from_url,
    build_source_from_youtube,
    load_csv_sources,
    locate_quote,
    source_id_from_text,
    split_into_chunks,
    url_source,
    youtube_source,
)
from hifc.storage import source_content_hash


def test_source_id_from_text_is_deterministic_and_hash_derived():
    text = "同じテキストは同じ source_id になる。"
    assert source_id_from_text(text) == source_id_from_text(text)
    assert source_id_from_text(text) == f"src-{source_content_hash(text)[:16]}"


def test_split_into_chunks_splits_on_blank_lines():
    text = "第一段落です。\n\n第二段落です。\n\n第三段落です。"
    chunks = split_into_chunks("src-x", text)
    assert [c.locator for c in chunks] == ["paragraph:1", "paragraph:2", "paragraph:3"]
    assert chunks[1].text == "第二段落です。"


def test_split_into_chunks_falls_back_to_sentences_for_long_single_paragraph():
    sentence = "これはテスト用の文です。"
    text = sentence * 40  # > 400 chars, no blank lines
    chunks = split_into_chunks("src-x", text)
    assert len(chunks) > 1
    assert all(c.locator.startswith("sentence:") for c in chunks)


def test_locate_quote_finds_containing_chunk():
    chunks = split_into_chunks("src-x", "第一段落です。\n\n第二段落の中に探したい文がある。")
    assert locate_quote(chunks, "探したい文") == "paragraph:2"
    assert locate_quote(chunks, "存在しない引用") is None


def test_build_source_from_paste_sets_content_hash_and_chunks():
    source = build_source_from_paste(
        person_id="taro",
        raw_text="自分の裁量で決めることを大切にしている。",
        source_type="blog",
        author_perspective="first_person",
        published_at=date(2026, 1, 1),
    )
    assert source.content_hash == source_content_hash(source.raw_text)
    assert source.source_id == source_id_from_text(source.raw_text)
    assert len(source.chunks) == 1


def test_build_source_from_file_reads_text_file(tmp_path):
    path = tmp_path / "note.md"
    path.write_text("ファイルからの取り込みテスト。", encoding="utf-8")
    source = build_source_from_file(
        path,
        person_id="taro",
        source_type="blog",
        author_perspective="first_person",
    )
    assert source.raw_text == "ファイルからの取り込みテスト。"
    assert source.origin == str(path)
    assert source.title == "note"


def test_build_source_from_file_rejects_unsupported_suffix(tmp_path):
    path = tmp_path / "note.docx"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(IngestError):
        build_source_from_file(
            path, person_id="taro", source_type="blog", author_perspective="first_person"
        )


def test_build_source_from_file_extracts_pdf_text(tmp_path, monkeypatch):
    import hifc.ingest.file_source as file_source

    monkeypatch.setattr(file_source, "extract_pdf_text", lambda path: "PDFから抽出したテキスト。")
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    source = build_source_from_file(
        path, person_id="taro", source_type="book", author_perspective="first_person"
    )
    assert source.raw_text == "PDFから抽出したテキスト。"


def test_load_csv_sources_uses_row_values_and_defaults(tmp_path):
    csv_path = tmp_path / "rows.csv"
    csv_path.write_text(
        "text,date,source_type,origin,author_perspective,title\n"
        "一行目のテキスト。,2026-01-01,blog,https://example.test/1,first_person,タイトル1\n"
        "二行目のテキスト。,,,,,\n"
        ",2026-01-01,blog,https://example.test/3,first_person,\n",
        encoding="utf-8",
    )
    sources = load_csv_sources(
        csv_path,
        person_id="taro",
        default_source_type="sns",
        default_author_perspective="third_party",
    )
    # blank text row is skipped
    assert len(sources) == 2
    assert sources[0].source_type == "blog"
    assert sources[0].published_at == date(2026, 1, 1)
    assert sources[1].source_type == "sns"
    assert sources[1].author_perspective == "third_party"
    assert sources[1].origin.startswith(f"csv:{csv_path.name}:row")


def test_load_csv_sources_raises_without_type_default(tmp_path):
    csv_path = tmp_path / "rows.csv"
    csv_path.write_text("text\n本文のみの行。\n", encoding="utf-8")
    with pytest.raises(IngestError):
        load_csv_sources(csv_path, person_id="taro", default_author_perspective="first_person")


_SAMPLE_ARTICLE_HTML = """
<html>
<head><title>サンプル記事</title></head>
<body>
<article>
<h1>サンプル記事</h1>
<p>これは一段落目の本文です。それなりの長さの文章にして抽出精度を上げます。</p>
<p>これは二段落目の本文です。複数の段落があることで記事らしい構造になります。</p>
<p>これは三段落目の本文です。さらに文章を追加して抽出対象を明確にします。</p>
</article>
</body>
</html>
"""


def test_build_source_from_html_extracts_article_text():
    source = build_source_from_html(
        _SAMPLE_ARTICLE_HTML,
        "https://example.test/article",
        person_id="taro",
        source_type="news",
        author_perspective="third_party",
    )
    assert "二段落目" in source.raw_text
    assert source.origin == "https://example.test/article"


def test_extract_video_id_supports_common_url_formats():
    assert youtube_source.extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert youtube_source.extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert (
        youtube_source.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3s")
        == "dQw4w9WgXcQ"
    )
    assert (
        youtube_source.extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ")
        == "dQw4w9WgXcQ"
    )
    with pytest.raises(YoutubeTranscriptUnavailable):
        youtube_source.extract_video_id("https://example.test/not-youtube")


def test_transcript_entries_to_text_groups_into_time_windows():
    entries = [
        {"text": "こんにちは", "start": 0.0, "duration": 2.0},
        {"text": "今日は天気がいいですね", "start": 3.0, "duration": 2.0},
        {"text": "次のトピックです", "start": 50.0, "duration": 2.0},
    ]
    text = youtube_source.transcript_entries_to_text(entries)
    paragraphs = text.split("\n\n")
    assert len(paragraphs) == 2
    assert "こんにちは" in paragraphs[0]
    assert "次のトピックです" in paragraphs[1]


def test_build_source_from_youtube_falls_back_when_transcript_unavailable(monkeypatch):
    def fake_fetch(video_id, *, languages=None):
        raise YoutubeTranscriptUnavailable("no captions")

    monkeypatch.setattr(youtube_source, "fetch_transcript_entries", fake_fetch)
    with pytest.raises(YoutubeTranscriptUnavailable):
        build_source_from_youtube(
            "https://youtu.be/dQw4w9WgXcQ",
            person_id="taro",
            author_perspective="first_person",
        )


def test_build_source_from_youtube_builds_source_document(monkeypatch):
    def fake_fetch(video_id, *, languages=None):
        return [
            {"text": "配信の冒頭コメントです", "start": 0.0, "duration": 3.0},
            {"text": "続きのコメントです", "start": 1.0, "duration": 3.0},
        ]

    monkeypatch.setattr(youtube_source, "fetch_transcript_entries", fake_fetch)
    source = build_source_from_youtube(
        "https://youtu.be/dQw4w9WgXcQ",
        person_id="taro",
        author_perspective="first_person",
    )
    assert source.source_type == "video_transcript"
    assert source.origin == "https://youtu.be/dQw4w9WgXcQ"
    assert "配信の冒頭コメントです" in source.raw_text


def test_validate_public_url_rejects_disallowed_scheme():
    with pytest.raises(UnsafeUrlError):
        url_source._validate_public_url("file:///etc/passwd")


def test_validate_public_url_rejects_loopback(monkeypatch):
    monkeypatch.setattr(
        url_source.socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [(None, None, None, None, ("127.0.0.1", 0))],
    )
    with pytest.raises(UnsafeUrlError):
        url_source._validate_public_url("http://localhost:8080/admin")


def test_validate_public_url_rejects_cloud_metadata_address(monkeypatch):
    monkeypatch.setattr(
        url_source.socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [(None, None, None, None, ("169.254.169.254", 0))],
    )
    with pytest.raises(UnsafeUrlError):
        url_source._validate_public_url("http://metadata.internal/latest/meta-data/")


def test_validate_public_url_rejects_private_rfc1918_address(monkeypatch):
    monkeypatch.setattr(
        url_source.socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [(None, None, None, None, ("10.0.0.5", 0))],
    )
    with pytest.raises(UnsafeUrlError):
        url_source._validate_public_url("http://internal-service/")


def test_validate_public_url_rejects_cgnat_shared_address_space(monkeypatch):
    # 100.64.0.0/10 (RFC 6598) is not `ipaddress.is_private` in Python, so a
    # denylist keyed on is_private/is_loopback/... alone would miss it; the
    # is_global-based allowlist must reject it anyway.
    monkeypatch.setattr(
        url_source.socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [(None, None, None, None, ("100.64.0.1", 0))],
    )
    with pytest.raises(UnsafeUrlError):
        url_source._validate_public_url("http://cgnat-host/")


def test_validate_public_url_allows_public_address(monkeypatch):
    monkeypatch.setattr(
        url_source.socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [(None, None, None, None, ("93.184.216.34", 0))],
    )
    url_source._validate_public_url("https://example.test/article")  # must not raise


def test_validate_public_url_wraps_dns_failure(monkeypatch):
    def fake_getaddrinfo(host, port, *a, **k):
        raise OSError("name resolution failed")

    monkeypatch.setattr(url_source.socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(UnsafeUrlError):
        url_source._validate_public_url("https://does-not-resolve.test/")


def test_fetch_html_rejects_redirect_to_internal_address(monkeypatch):
    def fake_getaddrinfo(host, port, *a, **k):
        try:
            import ipaddress as _ip

            _ip.ip_address(host)
            return [(None, None, None, None, (host, 0))]
        except ValueError:
            return [(None, None, None, None, ("93.184.216.34", 0))]

    monkeypatch.setattr(url_source.socket, "getaddrinfo", fake_getaddrinfo)

    call_count = {"n": 0}

    def fake_get(url, **kwargs):
        call_count["n"] += 1
        if url == "https://example.test/redirect":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/secret"})
        raise AssertionError(f"unexpected fetch of {url}")

    monkeypatch.setattr(url_source.httpx, "get", fake_get)

    with pytest.raises(UnsafeUrlError):
        url_source.fetch_html("https://example.test/redirect")
    assert call_count["n"] == 1


def test_build_source_from_url_rejects_local_target(monkeypatch):
    monkeypatch.setattr(
        url_source.socket,
        "getaddrinfo",
        lambda host, port, *a, **k: [(None, None, None, None, ("127.0.0.1", 0))],
    )
    with pytest.raises(UnsafeUrlError):
        build_source_from_url(
            "http://127.0.0.1:9000/internal-dashboard",
            person_id="taro",
            source_type="news",
            author_perspective="third_party",
        )


def _public_addrinfo(address: str = "93.184.216.34") -> list[tuple]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (address, 0))]


def _fake_response(status: int, url: str, *, text: str) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request("GET", url), text=text)


def test_fetch_html_wraps_http_status_error_as_ingest_error(monkeypatch):
    monkeypatch.setattr(
        url_source.socket, "getaddrinfo", lambda host, port, *a, **k: _public_addrinfo()
    )
    monkeypatch.setattr(
        url_source.httpx,
        "get",
        lambda url, **kwargs: _fake_response(404, url, text="not found"),
    )

    with pytest.raises(IngestError) as exc_info:
        url_source.fetch_html("https://example.test/missing")
    assert not isinstance(exc_info.value, url_source.UnsafeUrlError)
    assert "404" in str(exc_info.value)


def test_fetch_html_wraps_server_error_as_ingest_error(monkeypatch):
    monkeypatch.setattr(
        url_source.socket, "getaddrinfo", lambda host, port, *a, **k: _public_addrinfo()
    )
    monkeypatch.setattr(
        url_source.httpx,
        "get",
        lambda url, **kwargs: _fake_response(503, url, text="unavailable"),
    )

    with pytest.raises(IngestError):
        url_source.fetch_html("https://example.test/down")


def test_pinned_resolution_overrides_a_rebinding_resolver(monkeypatch):
    def rebinding_getaddrinfo(host, port, *args, **kwargs):
        # Simulates an attacker's DNS server: any *unpinned* lookup for this host
        # now resolves to an internal address instead of the one that was validated.
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.9", port or 0))]

    monkeypatch.setattr(url_source.socket, "getaddrinfo", rebinding_getaddrinfo)

    validated = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]
    with url_source._pinned_resolution("example.test", validated):
        pinned_result = socket.getaddrinfo("example.test", 443)
    assert pinned_result[0][4][0] == "93.184.216.34"

    # Outside the pin, resolution reverts to the (attacker-controlled) resolver.
    assert socket.getaddrinfo("example.test", 443)[0][4][0] == "10.0.0.9"


def test_fetch_html_connects_to_validated_address_despite_dns_rebinding(monkeypatch):
    lookups = {"n": 0}

    def rebinding_getaddrinfo(host, port, *args, **kwargs):
        lookups["n"] += 1
        if lookups["n"] == 1:
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", port or 0))]
        # A rebinding attacker flips the answer for any *later*, unpinned lookup.
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", port or 0))]

    monkeypatch.setattr(url_source.socket, "getaddrinfo", rebinding_getaddrinfo)

    connected_to = {}

    def fake_get(target_url, **kwargs):
        # Mirrors what httpcore's sync backend does: resolve again at connect time.
        host = url_source.urlparse(target_url).hostname
        info = socket.getaddrinfo(host, 443)
        connected_to["address"] = info[0][4][0]
        return httpx.Response(200, request=httpx.Request("GET", target_url), text="ok")

    monkeypatch.setattr(url_source.httpx, "get", fake_get)

    url_source.fetch_html("https://example.test/article")

    assert connected_to["address"] == "93.184.216.34"
    # The pin intercepts the connect-time lookup entirely: the (rebinding) real
    # resolver is only ever consulted once, at validation time.
    assert lookups["n"] == 1
