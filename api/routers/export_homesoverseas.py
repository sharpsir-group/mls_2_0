# Copyright 2025 SharpSir Group
# Licensed under the Apache License, Version 2.0
# See LICENSE file for details.
"""
HomeOverseas.ru XML Feed Export (V4)

Public endpoint that generates an XML feed from the exports.homesoverseas
staging table in Databricks.  No authentication required — HomeOverseas
fetches this URL directly.

Spec: HomeOverseas.ru XML Feed Technical Requirements V4 (1.05.2023)
"""
import re
import time
import json
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.sax.saxutils import escape

from fastapi import APIRouter, Response, Path as PathParam
from fastapi.responses import Response as FastAPIResponse

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_settings
from services.databricks import get_databricks_connector


router = APIRouter(tags=["Exports"])

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------
_cache: dict[str, Any] = {
    "xml_bytes": None,
    "generated_at": 0.0,
}
# Cache for limited feed: key = limit (e.g. 1000), value = {xml_bytes, generated_at}
_cache_limited: dict[int, dict[str, Any]] = {}
_CACHE_TTL_SECONDS = 900  # 15 minutes default
_MAX_LIMIT = 10000


def _get_cache_ttl() -> int:
    """Read TTL from env or fall back to default."""
    import os
    try:
        return int(os.getenv("HOMESOVERSEAS_CACHE_TTL_SECONDS", str(_CACHE_TTL_SECONDS)))
    except ValueError:
        return _CACHE_TTL_SECONDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_youtube_id(url: Optional[str]) -> Optional[str]:
    """Extract YouTube video ID from a URL, or return None."""
    if not url:
        return None
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def _add_text(parent: Element, tag: str, text: Optional[str]) -> None:
    """Add a child element with text content (skip if text is None/empty)."""
    if text is not None and str(text).strip():
        el = SubElement(parent, tag)
        el.text = str(text).strip()


def _add_multilang(parent: Element, tag: str, ru: str, en: str) -> None:
    """Add a multilingual element with <ru> and <en> children."""
    wrapper = SubElement(parent, tag)
    if ru and ru.strip():
        ru_el = SubElement(wrapper, "ru")
        ru_el.text = ru
    en_el = SubElement(wrapper, "en")
    en_el.text = en if en else ""


def _add_cdata_multilang(parent: Element, tag: str, ru: str, en: str) -> None:
    """
    Add a multilingual element with CDATA-wrapped children.

    ElementTree doesn't natively support CDATA, so we use a sentinel
    that is replaced in the final serialized XML string.
    """
    wrapper = SubElement(parent, tag)
    if ru and ru.strip():
        ru_el = SubElement(wrapper, "ru")
        ru_el.text = f"__CDATA_START__{ru}__CDATA_END__"
    en_el = SubElement(wrapper, "en")
    en_el.text = f"__CDATA_START__{en}__CDATA_END__" if en else ""


def _fixup_cdata(xml_str: str) -> str:
    """Replace CDATA sentinels with real CDATA sections.

    ElementTree escapes special chars in text nodes, but content inside
    CDATA must remain unescaped.  After swapping the sentinels we reverse
    the XML entity encoding within each CDATA block.
    """
    xml_str = xml_str.replace("__CDATA_START__", "<![CDATA[")
    xml_str = xml_str.replace("__CDATA_END__", "]]>")

    # Un-escape HTML entities inside CDATA blocks
    def _unescape_cdata(m: re.Match) -> str:
        inner = m.group(1)
        inner = inner.replace("&amp;", "&")
        inner = inner.replace("&lt;", "<")
        inner = inner.replace("&gt;", ">")
        inner = inner.replace("&apos;", "'")
        inner = inner.replace("&quot;", '"')
        return f"<![CDATA[{inner}]]>"

    xml_str = re.sub(r"<!\[CDATA\[(.*?)\]\]>", _unescape_cdata, xml_str, flags=re.DOTALL)
    return xml_str


def _transform_media_url(url: str) -> str:
    """Ensure media URL is absolute (prepend Qobrix domain if relative)."""
    if not url:
        return url
    if url.startswith("/"):
        settings = get_settings()
        base = settings.qobrix_api_base_url
        if base and "/api/" in base:
            base = base.split("/api/")[0]
        return f"{base}{url}" if base else url
    return url


# ---------------------------------------------------------------------------
# XML builder
# ---------------------------------------------------------------------------

def build_xml(rows: list[dict[str, Any]]) -> bytes:
    """
    Build the HomeOverseas V4 XML from export rows.

    Returns UTF-8 encoded XML bytes.
    """
    root = Element("root")

    # <meta>
    meta = SubElement(root, "meta")
    ver = SubElement(meta, "version")
    ver.text = "4"
    ts = SubElement(meta, "timestamp")
    ts.text = datetime.now(timezone.utc).isoformat()

    # <objects>
    objects = SubElement(root, "objects")

    for row in rows:
        obj = SubElement(objects, "object")

        # -- mandatory --
        _add_text(obj, "objectid", row.get("objectid"))
        _add_text(obj, "ref", row.get("ref"))

        # title (multilingual)
        _add_multilang(obj, "title", row.get("title_ru", ""), row.get("title_en", ""))

        # type (sale/rent)
        _add_text(obj, "type", row.get("listing_type"))

        # market
        if row.get("market"):
            _add_text(obj, "market", row["market"])

        # annotation (multilingual)
        _add_multilang(
            obj, "annotation",
            row.get("annotation_ru", ""),
            row.get("annotation_en", ""),
        )

        # description (multilingual, CDATA)
        _add_cdata_multilang(
            obj, "description",
            row.get("description_ru", ""),
            row.get("description_en", ""),
        )

        # price
        price_el = SubElement(obj, "price")
        listing_type = row.get("listing_type", "sale")
        if listing_type == "sale":
            sale_val = row.get("sale_price")
            _add_text(price_el, "sale", str(int(sale_val)) if sale_val is not None else "0")
        else:
            # rent — emit whichever periods are populated
            for period in ("day", "week", "month", "year"):
                val = row.get(f"rent_{period}")
                if val is not None:
                    _add_text(price_el, period, str(int(val)))
            # if none were set, default to month=0 (price on request)
            if not list(price_el):
                _add_text(price_el, "month", "0")

        # price_from
        if row.get("price_from") == "Y":
            _add_text(obj, "price_from", "Y")

        # currency
        _add_text(obj, "currency", row.get("currency", "eur"))

        # region
        _add_text(obj, "region", row.get("region"))

        # realty_type
        _add_text(obj, "realty_type", row.get("realty_type"))

        # optional detail fields
        if row.get("bedrooms") is not None:
            _add_text(obj, "bedrooms", row["bedrooms"])

        if row.get("size_house") is not None:
            val = row["size_house"]
            try:
                val = int(float(val))
            except (ValueError, TypeError):
                val = None
            if val and val > 0:
                _add_text(obj, "size_house", str(val))

        if row.get("size_land") is not None:
            val = row["size_land"]
            try:
                val = int(float(val))
            except (ValueError, TypeError):
                val = None
            if val and val > 0:
                _add_text(obj, "size_land", str(val))

        if row.get("year_built") is not None:
            try:
                yr = int(row["year_built"])
            except (ValueError, TypeError):
                yr = 0
            if 1500 <= yr <= 2099:
                _add_text(obj, "year", str(yr))

        if row.get("level") is not None:
            try:
                lv = int(row["level"])
            except (ValueError, TypeError):
                lv = -1
            if lv >= 0:
                _add_text(obj, "level", str(lv))

        if row.get("levels") is not None:
            _add_text(obj, "levels", row["levels"])

        if row.get("distance_aero") is not None:
            _add_text(obj, "distance_aero", row["distance_aero"])

        if row.get("distance_sea") is not None:
            _add_text(obj, "distance_sea", row["distance_sea"])

        # options
        options_csv = row.get("options_csv", "")
        if options_csv:
            option_ids = [o.strip() for o in str(options_csv).split(",") if o.strip()]
            if option_ids:
                opts_el = SubElement(obj, "options")
                for oid in option_ids:
                    _add_text(opts_el, "option", oid)

        # coordinates
        if row.get("lat") is not None and row.get("lng") is not None:
            _add_text(obj, "lat", row["lat"])
            _add_text(obj, "lng", row["lng"])
            _add_text(obj, "exact_coords", "Y")

        # photos
        photo_urls = row.get("photo_urls")
        if photo_urls:
            # photo_urls comes from Databricks as a JSON array string or a list
            if isinstance(photo_urls, str):
                try:
                    photo_urls = json.loads(photo_urls)
                except (json.JSONDecodeError, TypeError):
                    photo_urls = []
            if photo_urls:
                photos_el = SubElement(obj, "photos")
                for url in photo_urls[:15]:
                    if url:
                        full_url = _transform_media_url(str(url))
                        _add_text(photos_el, "photo", full_url)

        # YouTube video
        ytid = _extract_youtube_id(row.get("video_link"))
        if ytid:
            _add_text(obj, "ytid", ytid)

        # developer flag
        if row.get("developer_flag") == "Y":
            _add_text(obj, "developer", "Y")

    # Serialize to string, apply CDATA fixup, encode to bytes
    raw_xml = tostring(root, encoding="unicode", xml_declaration=False)
    raw_xml = _fixup_cdata(raw_xml)
    full_xml = '<?xml version="1.0" encoding="utf-8" ?>\n' + raw_xml
    return full_xml.encode("utf-8")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/export/homesoverseas.xml",
    summary="HomeOverseas.ru XML Feed V4",
    description=(
        "Public XML feed of active Cyprus property listings formatted for "
        "HomeOverseas.ru V4 specification. No authentication required."
    ),
    response_class=FastAPIResponse,
)
async def homesoverseas_xml():
    """
    Generate and return the HomeOverseas V4 XML feed.

    Results are cached in-memory for HOMESOVERSEAS_CACHE_TTL_SECONDS
    (default 15 min) to avoid hitting Databricks on every request.
    """
    ttl = _get_cache_ttl()
    now = time.time()

    # Return cached version if still fresh
    if _cache["xml_bytes"] is not None and (now - _cache["generated_at"]) < ttl:
        return Response(
            content=_cache["xml_bytes"],
            media_type="application/xml; charset=utf-8",
            headers={"X-Cache": "HIT"},
        )

    # Query Databricks
    settings = get_settings()
    connector = get_databricks_connector()
    catalog = settings.databricks_catalog

    sql = f"""
        SELECT *
        FROM {catalog}.exports.homesoverseas
        ORDER BY listing_created_date DESC, objectid DESC
        LIMIT 1000
    """

    result = await connector.execute_query(sql)

    columns = result.get("columns", [])
    data_rows = result.get("data", [])

    # Convert to list of dicts
    rows = [dict(zip(columns, row)) for row in data_rows]

    # Build XML
    xml_bytes = build_xml(rows)

    # Update cache
    _cache["xml_bytes"] = xml_bytes
    _cache["generated_at"] = time.time()

    return Response(
        content=xml_bytes,
        media_type="application/xml; charset=utf-8",
        headers={"X-Cache": "MISS"},
    )


@router.get(
    "/export/homesoverseas.xml/{limit}",
    summary="HomeOverseas.ru XML Feed V4 (limited, newest first)",
    description=(
        "Same XML feed as /export/homesoverseas.xml but limited to N objects "
        "sorted by listing creation date (newest first). E.g. /export/homesoverseas.xml/1000 returns 1000 newest."
    ),
    response_class=FastAPIResponse,
)
async def homesoverseas_xml_limited(
    limit: int = PathParam(ge=1, le=_MAX_LIMIT, description="Max number of objects (newest first)"),
):
    """
    Generate XML feed with only the N newest listings (by listing_created_date DESC).
    Same format as full feed. Cached per limit.
    """
    ttl = _get_cache_ttl()
    now = time.time()
    entry = _cache_limited.get(limit)
    if entry and (now - entry["generated_at"]) < ttl:
        return Response(
            content=entry["xml_bytes"],
            media_type="application/xml; charset=utf-8",
            headers={"X-Cache": "HIT", "X-Limit": str(limit)},
        )

    settings = get_settings()
    connector = get_databricks_connector()
    catalog = settings.databricks_catalog

    sql = f"""
        SELECT *
        FROM {catalog}.exports.homesoverseas
        ORDER BY objectid DESC
        LIMIT {limit}
    """

    result = await connector.execute_query(sql)
    columns = result.get("columns", [])
    data_rows = result.get("data", [])
    rows = [dict(zip(columns, row)) for row in data_rows]
    xml_bytes = build_xml(rows)

    _cache_limited[limit] = {"xml_bytes": xml_bytes, "generated_at": time.time()}

    return Response(
        content=xml_bytes,
        media_type="application/xml; charset=utf-8",
        headers={"X-Cache": "MISS", "X-Limit": str(limit)},
    )
