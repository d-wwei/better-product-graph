"""Mechanical safety and exact binding for reader-visible PRD visuals.

The editable SVG is the review truth.  A PNG is an optional Handoff derivative,
never a prerequisite for Candidate freeze or content Review.
"""

from __future__ import annotations

import re
import struct
import zlib
from fractions import Fraction
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from xml.etree import ElementTree

from .storage import sha256_bytes


class VisualAssetError(ValueError):
    """A reader-visible visual asset is missing, unsafe, or not exact."""


SVG_NAMESPACE = "http://www.w3.org/2000/svg"
VISUAL_REF_VERSION = "reader-visual.v1"
VISUAL_SOURCE_SCAN_VERSION = "visual-source-scan.v1"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MIN_RASTER_SHORT_SIDE = 320
MIN_RASTER_LONG_SIDE = 640
MAX_RASTER_SIDE = 16_384
MAX_RASTER_PIXELS = 64_000_000
MIN_SVG_VIEWBOX_DIMENSION = Fraction(1, 1_000_000)
MAX_SVG_VIEWBOX_VALUE = Fraction(1_000_000_000)
MAX_SVG_VIEWBOX_EXPONENT = 12
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"

_REFERENCE_DEFINITION = re.compile(
    r"^[ \t]{0,3}\[([^\]\n]+)\]:[ \t]*<?([^\s>]+)>?(?:[ \t]+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?[ \t]*$",
    re.M,
)
_INLINE_IMAGE = re.compile(
    r"!\[([^\]\n]*)\]\([ \t]*<?([^\s)>]+)>?(?:[ \t]+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?[ \t]*\)"
)
_REFERENCE_IMAGE = re.compile(r"!\[([^\]\n]*)\]\[([^\]\n]*)\]")
_SHORTCUT_IMAGE = re.compile(r"!\[([^\]\n]+)\](?![\[(])")
_RAW_IMAGE = re.compile(r"<img\b[^>]*>", re.I)
_HTML_SRC = re.compile(r"\bsrc\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
_RAW_INLINE_SVG = re.compile(r"<\s*svg\b", re.I)
_SAFE_VIEWBOX_NUMBER = re.compile(
    r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE](?P<exponent>[+-]?\d+))?"
)
_URI_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
_KNOWN_VISUAL_SUFFIXES = (
    ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".bmp", ".ico",
)
_MERMAID_HEADER = re.compile(
    r"^(?:flowchart|graph|sequenceDiagram|stateDiagram(?:-v2)?|classDiagram|"
    r"erDiagram|journey|gantt|mindmap|timeline|quadrantChart|xychart-beta)\b"
)

_ALLOWED_SVG_ELEMENTS = {
    "svg", "g", "title", "desc", "text", "tspan", "path", "rect",
    "circle", "ellipse", "line", "polyline", "polygon", "defs", "marker",
    "clipPath", "use",
}
_ALLOWED_SVG_ATTRIBUTES = {
    "id", "role", "aria-label", "aria-labelledby", "viewBox",
    "preserveAspectRatio", "x", "y", "x1", "y1", "x2", "y2",
    "cx", "cy", "r", "rx", "ry", "width", "height", "dx", "dy",
    "d", "points", "transform", "fill", "fill-opacity", "fill-rule",
    "stroke", "stroke-width", "stroke-opacity", "stroke-linecap",
    "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset", "opacity",
    "font-size", "font-family", "font-weight", "text-anchor",
    "dominant-baseline", "refX", "refY", "markerWidth", "markerHeight",
    "markerUnits", "orient", "clipPathUnits", "clip-path", "marker-start",
    "marker-mid", "marker-end", "vector-effect", "href", "filter",
    "mask", "title", "data-text",
}

_LOCAL_FRAGMENT_ATTRIBUTES = {"href"}
_LOCAL_URL_ATTRIBUTES = {
    "clip-path", "filter", "mask", "marker-start", "marker-mid", "marker-end",
}


def _mask_range(characters: list[str], start: int, end: int) -> None:
    for index in range(start, end):
        if characters[index] not in "\r\n":
            characters[index] = " "


def _fence_token(line: str, *, closing: bool = False) -> str | None:
    content = line.rstrip("\r\n")
    match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", content)
    if match is None:
        return None
    token, remainder = match.groups()
    if closing:
        return token if not remainder.strip(" \t") else None
    if token[0] == "`" and "`" in remainder:
        return None
    return token


def _mask_block_code(markdown: str) -> str:
    """Mask fenced and indented code before interpreting any HTML comment.

    The pass preserves every newline and byte position.  A comment opener in a
    code literal therefore cannot turn the remainder of the document into an
    apparent comment before the Markdown code boundary is known.
    """

    characters = list(markdown)
    offset = 0
    marker: str | None = None
    marker_length = 0
    for line in markdown.splitlines(keepends=True):
        if marker is None:
            token = _fence_token(line)
            if token is not None:
                marker = token[0]
                marker_length = len(token)
                _mask_range(characters, offset, offset + len(line))
            elif re.match(r"^(?: {4}|\t)", line):
                _mask_range(characters, offset, offset + len(line))
        else:
            _mask_range(characters, offset, offset + len(line))
            token = _fence_token(line, closing=True)
            if token is not None and token[0] == marker and len(token) >= marker_length:
                marker = None
                marker_length = 0
        offset += len(line)
    return "".join(characters)


def _mask_inline_code_and_html_comments(markdown: str) -> str:
    """Mask inline code and comments in source order after block-code masking.

    Whichever construct starts first owns its contents: a comment's backticks
    cannot pair with later source, while a code span's comment marker remains a
    literal.  This avoids either grammar hiding later active visuals.
    """

    characters = list(markdown)
    index = 0
    while index < len(markdown):
        if markdown.startswith("<!--", index):
            closing = markdown.find("-->", index + 4)
            end = len(markdown) if closing < 0 else closing + 3
            _mask_range(characters, index, end)
            index = end
            continue
        if markdown[index] != "`" or _is_escaped(markdown, index):
            index += 1
            continue
        run_end = index
        while run_end < len(markdown) and markdown[run_end] == "`":
            run_end += 1
        run_length = run_end - index
        cursor = run_end
        closer_end: int | None = None
        while cursor < len(markdown):
            candidate = markdown.find("`", cursor)
            if candidate < 0:
                break
            candidate_end = candidate
            while candidate_end < len(markdown) and markdown[candidate_end] == "`":
                candidate_end += 1
            if candidate_end - candidate == run_length:
                closer_end = candidate_end
                break
            cursor = candidate_end
        if closer_end is None:
            index = run_end
            continue
        _mask_range(characters, index, closer_end)
        index = closer_end
    return "".join(characters)


def _rendered_markdown_source(markdown: str) -> str:
    without_block_code = _mask_block_code(markdown)
    return _mask_inline_code_and_html_comments(without_block_code)


def _is_escaped(source: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and source[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def _normalized_reference_label(label: str) -> str:
    return " ".join(label.split()).casefold()


def _safe_asset_name(raw: str) -> PurePosixPath:
    value = PurePosixPath(raw)
    if (
        value.is_absolute() or not value.parts or ".." in value.parts
        or "." in value.parts or "\\" in raw or raw.startswith("/")
        or any(character in raw for character in ("\0", "%", "?", "#"))
    ):
        raise VisualAssetError(f"unsafe reader-visible asset path: {raw}")
    return value


def _managed_svg_destination(destination: str) -> str:
    if not destination.startswith("./assets/"):
        raise VisualAssetError(
            f"reader-visible image must be a managed local SVG: {destination}"
        )
    name = _safe_asset_name(destination[len("./assets/") :]).as_posix()
    if not name.casefold().endswith(".svg"):
        raise VisualAssetError(
            f"reader-visible image must use a managed SVG: {destination}"
        )
    return name


def _reader_visible_svg_names(markdown: str) -> list[str]:
    source = _rendered_markdown_source(markdown)
    if _RAW_INLINE_SVG.search(source):
        raise VisualAssetError(
            "reader-visible raw inline SVG is forbidden; use a managed SVG/PNG pair"
        )
    definitions = {
        _normalized_reference_label(label): destination
        for label, destination in _REFERENCE_DEFINITION.findall(source)
    }
    occurrences: list[tuple[int, str]] = []
    occupied: list[tuple[int, int]] = []
    for match in _INLINE_IMAGE.finditer(source):
        if _is_escaped(source, match.start()):
            continue
        occurrences.append((match.start(), match.group(2)))
        occupied.append(match.span())
    for match in _REFERENCE_IMAGE.finditer(source):
        if _is_escaped(source, match.start()):
            continue
        label = _normalized_reference_label(match.group(2) or match.group(1))
        destination = definitions.get(label)
        if destination is None:
            raise VisualAssetError(f"reader-visible image reference is unresolved: {label}")
        occurrences.append((match.start(), destination))
        occupied.append(match.span())
    for match in _SHORTCUT_IMAGE.finditer(source):
        if _is_escaped(source, match.start()):
            continue
        if any(start <= match.start() < end for start, end in occupied):
            continue
        label = _normalized_reference_label(match.group(1))
        destination = definitions.get(label)
        if destination is None:
            raise VisualAssetError(f"reader-visible image reference is unresolved: {label}")
        occurrences.append((match.start(), destination))
    for match in _RAW_IMAGE.finditer(source):
        src = _HTML_SRC.search(match.group(0))
        if src is None:
            raise VisualAssetError("reader-visible image HTML requires a src")
        occurrences.append(
            (match.start(), next(value for value in src.groups() if value is not None))
        )

    names: list[str] = []
    for _, destination in sorted(occurrences):
        name = _managed_svg_destination(destination)
        if name not in names:
            names.append(name)
    return names


def _local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _namespace(name: str) -> str | None:
    if name.startswith("{") and "}" in name:
        return name[1 : name.index("}")]
    return None


def _positive_view_box(root: ElementTree.Element) -> tuple[Fraction, Fraction]:
    raw = root.attrib.get("viewBox")
    if not isinstance(raw, str):
        raise VisualAssetError("reader-visible SVG requires a viewBox")
    parts = re.split(r"[\s,]+", raw.strip())
    if len(parts) != 4:
        raise VisualAssetError("reader-visible SVG viewBox must contain four numbers")
    values: list[Fraction] = []
    for value in parts:
        match = _SAFE_VIEWBOX_NUMBER.fullmatch(value) if len(value) <= 64 else None
        if match is None:
            raise VisualAssetError("reader-visible SVG viewBox must contain safe numbers")
        exponent = match.group("exponent")
        if exponent is not None:
            unsigned_exponent = exponent.lstrip("+-")
            if (
                len(unsigned_exponent) > 3
                or abs(int(exponent)) > MAX_SVG_VIEWBOX_EXPONENT
            ):
                raise VisualAssetError(
                    "reader-visible SVG viewBox values must stay within the safe range"
                )
        try:
            parsed = Fraction(value)
        except (ValueError, ZeroDivisionError) as error:
            raise VisualAssetError(
                "reader-visible SVG viewBox must contain safe numbers"
            ) from error
        if abs(parsed) > MAX_SVG_VIEWBOX_VALUE:
            raise VisualAssetError(
                "reader-visible SVG viewBox values must stay within the safe range"
            )
        values.append(parsed)
    if (
        values[2] < MIN_SVG_VIEWBOX_DIMENSION
        or values[3] < MIN_SVG_VIEWBOX_DIMENSION
    ):
        raise VisualAssetError(
            "reader-visible SVG requires a positive viewBox within the safe range"
        )
    return values[2], values[3]


def _validate_svg(content: bytes) -> tuple[Fraction, Fraction]:
    try:
        source = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise VisualAssetError("reader-visible SVG must be UTF-8 XML") from error
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", source, re.I):
        raise VisualAssetError("reader-visible SVG cannot declare active XML content")
    try:
        for event, payload in ElementTree.iterparse(
            BytesIO(content), events=("pi", "start-ns")
        ):
            if event == "pi":
                raise VisualAssetError(
                    "reader-visible SVG cannot contain processing instructions"
                )
            prefix, value = payload
            if not (
                (not prefix and value == SVG_NAMESPACE)
                or (prefix == "xlink" and value == XLINK_NAMESPACE)
            ):
                raise VisualAssetError("reader-visible SVG contains an unsafe namespace")
    except ElementTree.ParseError as error:
        raise VisualAssetError("reader-visible SVG must be well-formed XML") from error
    try:
        root = ElementTree.fromstring(source)
    except ElementTree.ParseError as error:
        raise VisualAssetError("reader-visible SVG must be well-formed XML") from error
    if root.tag != f"{{{SVG_NAMESPACE}}}svg":
        raise VisualAssetError("reader-visible SVG must use the standard SVG namespace")

    width, height = _positive_view_box(root)
    accessible_text = False
    visible_text = False
    for element in root.iter():
        if _namespace(element.tag) != SVG_NAMESPACE:
            raise VisualAssetError("reader-visible SVG contains an unsafe namespace")
        tag = _local_name(element.tag)
        if tag not in _ALLOWED_SVG_ELEMENTS:
            raise VisualAssetError(f"reader-visible SVG cannot contain {tag}")
        element_text = "".join(element.itertext()).strip()
        if tag in {"title", "desc"} and element_text:
            accessible_text = True
        if tag == "text" and element_text:
            visible_text = True
        for raw_name, raw_value in element.attrib.items():
            attribute_namespace = _namespace(raw_name)
            name = _local_name(raw_name)
            if attribute_namespace not in {None, XLINK_NAMESPACE}:
                raise VisualAssetError("reader-visible SVG contains an unsafe namespace")
            if attribute_namespace == XLINK_NAMESPACE and name != "href":
                raise VisualAssetError("reader-visible SVG contains an unsafe namespace")
            if name not in _ALLOWED_SVG_ATTRIBUTES:
                raise VisualAssetError(
                    f"reader-visible SVG contains unsafe attribute {name}"
                )
            value = str(raw_value).strip()
            if name in _LOCAL_FRAGMENT_ATTRIBUTES:
                if re.fullmatch(r"#[A-Za-z_][\w:.-]*", value) is None:
                    raise VisualAssetError(
                        "reader-visible SVG references must use a local #fragment"
                    )
            elif name in _LOCAL_URL_ATTRIBUTES:
                if value.casefold() != "none" and re.fullmatch(
                    r"url\(\s*#[A-Za-z_][\w:.-]*\s*\)", value, re.I
                ) is None:
                    raise VisualAssetError(
                        "reader-visible SVG references must use a local #fragment"
                    )
            elif name in {"fill", "stroke"}:
                if value.casefold().startswith("url"):
                    if re.fullmatch(
                        r"url\(\s*#[A-Za-z_][\w:.-]*\s*\)", value, re.I
                    ) is None:
                        raise VisualAssetError(
                            "reader-visible SVG references must use a local #fragment"
                        )
                elif "\\" in value or "//" in value or _URI_SCHEME.search(value):
                    raise VisualAssetError(
                        "reader-visible SVG cannot contain external content"
                    )
            if name == "aria-label" and value:
                accessible_text = True
    if not accessible_text:
        raise VisualAssetError("reader-visible SVG requires text or an accessibility alternative")
    if not visible_text:
        raise VisualAssetError("reader-visible SVG requires a visible text label")
    return width, height


def _png_dimensions(content: bytes) -> tuple[int, int]:
    if len(content) < 8 or content[:8] != PNG_SIGNATURE:
        raise VisualAssetError("reader-visible PNG has an invalid signature")
    offset = 8
    chunks: list[bytes] = []
    width = height = 0
    color_type = bit_depth = -1
    seen_idat = idat_ended = seen_iend = seen_plte = False
    idat_bytes = 0
    palette_entries = 0
    seen_transparency = False
    legal_depths = {
        0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8},
        4: {8, 16}, 6: {8, 16},
    }
    while offset < len(content):
        if len(content) - offset < 12:
            raise VisualAssetError("reader-visible PNG chunk stream is truncated")
        length = struct.unpack(">I", content[offset : offset + 4])[0]
        chunk_type = content[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(content):
            raise VisualAssetError("reader-visible PNG chunk stream is truncated")
        payload = content[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", content[offset + 8 + length : end])[0]
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != expected_crc:
            raise VisualAssetError("reader-visible PNG chunk checksum is invalid")
        if len(chunk_type) != 4 or not all(
            65 <= byte <= 90 or 97 <= byte <= 122 for byte in chunk_type
        ):
            raise VisualAssetError("reader-visible PNG has an invalid chunk type")
        if seen_iend:
            raise VisualAssetError("reader-visible PNG contains trailing data")
        if not chunks and chunk_type != b"IHDR":
            raise VisualAssetError("reader-visible PNG requires IHDR first")
        if chunk_type == b"IHDR":
            if chunks or length != 13:
                raise VisualAssetError("reader-visible PNG requires one valid IHDR")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if width <= 0 or height <= 0:
                raise VisualAssetError("reader-visible PNG requires positive dimensions")
            if (
                width > MAX_RASTER_SIDE
                or height > MAX_RASTER_SIDE
                or width * height > MAX_RASTER_PIXELS
            ):
                raise VisualAssetError("reader-visible PNG exceeds safe raster resource limits")
            if color_type not in legal_depths or bit_depth not in legal_depths[color_type]:
                raise VisualAssetError("reader-visible PNG has an invalid IHDR encoding")
            if compression != 0 or filtering != 0 or interlace not in {0, 1}:
                raise VisualAssetError("reader-visible PNG has an invalid IHDR encoding")
        elif chunk_type == b"PLTE":
            if seen_plte or seen_idat or length == 0 or length % 3 or length > 768:
                raise VisualAssetError("reader-visible PNG has an invalid PLTE")
            if color_type in {0, 4}:
                raise VisualAssetError("reader-visible grayscale PNG cannot contain PLTE")
            seen_plte = True
            palette_entries = length // 3
            if color_type == 3 and palette_entries > 2**bit_depth:
                raise VisualAssetError("reader-visible indexed PNG PLTE exceeds bit depth")
        elif chunk_type == b"tRNS":
            if seen_transparency or seen_idat or color_type in {4, 6}:
                raise VisualAssetError("reader-visible PNG has an invalid tRNS")
            if (
                (color_type == 0 and length != 2)
                or (color_type == 2 and length != 6)
                or (color_type == 3 and (not seen_plte or not 0 < length <= palette_entries))
            ):
                raise VisualAssetError("reader-visible PNG has an invalid tRNS")
            seen_transparency = True
        elif chunk_type == b"IDAT":
            if idat_ended:
                raise VisualAssetError("reader-visible PNG IDAT chunks must be consecutive")
            if color_type == 3 and not seen_plte:
                raise VisualAssetError("reader-visible indexed PNG requires PLTE")
            seen_idat = True
            idat_bytes += length
        elif chunk_type == b"IEND":
            if length != 0 or not seen_idat:
                raise VisualAssetError("reader-visible PNG requires IDAT before IEND")
            seen_iend = True
        else:
            if seen_idat:
                idat_ended = True
            if chunk_type[:1].isupper():
                raise VisualAssetError(
                    f"reader-visible PNG contains unsupported critical chunk {chunk_type.decode('ascii')}"
                )
        chunks.append(chunk_type)
        offset = end
    if not seen_idat or idat_bytes <= 0 or not seen_iend or chunks[-1:] != [b"IEND"]:
        raise VisualAssetError("reader-visible PNG requires complete IDAT and IEND chunks")
    return width, height


def _validate_visual_pair_payloads(
    svg_name: str,
    assets: Mapping[str, bytes],
    *,
    referenced: bool,
) -> dict[str, Any]:
    """Validate one exact managed SVG source and an optional PNG derivative."""

    png_name = f"{svg_name[:-4]}@2x.png"
    vector = assets.get(svg_name)
    raster = assets.get(png_name)
    if not isinstance(vector, bytes):
        raise VisualAssetError(f"missing reader-visible SVG: {svg_name}")
    try:
        svg_width, svg_height = _validate_svg(vector)
    except VisualAssetError as error:
        label = "reader-visible SVG" if referenced else "malicious orphan SVG"
        raise VisualAssetError(f"{label} {svg_name} is unsafe: {error}") from error
    png_width = png_height = None
    if raster is not None:
        if not isinstance(raster, bytes):
            raise VisualAssetError(f"reader-visible PNG payload must be bytes: {png_name}")
        png_width, png_height = _png_dimensions(raster)
        if (
            min(png_width, png_height) < MIN_RASTER_SHORT_SIDE
            or max(png_width, png_height) < MIN_RASTER_LONG_SIDE
        ):
            raise VisualAssetError(
                f"reader-visible PNG {png_name} requires at least "
                f"{MIN_RASTER_SHORT_SIDE}px short side and {MIN_RASTER_LONG_SIDE}px long side"
            )
        aspect_difference = abs(
            Fraction(png_width) * svg_height
            - svg_width * Fraction(png_height)
        )
        expected_cross_product = svg_width * Fraction(png_height)
        if aspect_difference * 100 > expected_cross_product * 5:
            raise VisualAssetError(
                f"reader-visible PNG {png_name} must preserve the SVG aspect ratio within 5%"
            )
    result = {
        "svg_name": svg_name,
        "png_name": png_name if raster is not None else None,
        "svg_dimensions": [str(svg_width), str(svg_height)],
        "png_dimensions": (
            [png_width, png_height] if raster is not None else None
        ),
    }
    mermaid_name = f"{svg_name[:-4]}.mmd"
    if mermaid_name in assets:
        result["mermaid_name"] = mermaid_name
    return result


def _validate_mermaid_source(name: str, content: bytes) -> None:
    try:
        source = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise VisualAssetError(f"Mermaid source must be UTF-8: {name}") from error
    if len(content) > 1_000_000:
        raise VisualAssetError(f"Mermaid source exceeds the safe size limit: {name}")
    first = next(
        (line.strip() for line in source.splitlines() if line.strip() and not line.lstrip().startswith("%%")),
        "",
    )
    if _MERMAID_HEADER.match(first) is None:
        raise VisualAssetError(f"Mermaid source uses an unsupported diagram type: {name}")
    if re.search(
        r"%%\{|\bclick\b|<\s*script\b|javascript:|data:|https?://",
        source,
        flags=re.I,
    ):
        raise VisualAssetError(f"Mermaid source contains active or external content: {name}")


def validate_reader_visible_asset_payloads(
    markdown: str, assets: Mapping[str, bytes]
) -> list[dict[str, Any]]:
    """Validate rendered Markdown SVG sources and optional PNG derivatives."""

    pairs: list[dict[str, Any]] = []
    for svg_name in _reader_visible_svg_names(markdown):
        pairs.append(
            _validate_visual_pair_payloads(svg_name, assets, referenced=True)
        )
    return pairs


def validate_managed_visual_asset_tree(
    markdown: str,
    assets: Mapping[str, bytes],
    *,
    require_png: bool = True,
) -> list[dict[str, Any]]:
    """Validate every visual in a strict Profile's final immutable asset tree."""

    referenced = set(_reader_visible_svg_names(markdown))
    normalized: dict[str, bytes] = {}
    for raw_name, payload in assets.items():
        if not isinstance(raw_name, str):
            raise VisualAssetError("visual asset name must be a string")
        name = _safe_asset_name(raw_name).as_posix()
        if name in normalized:
            raise VisualAssetError(f"duplicate visual asset name: {name}")
        if not isinstance(payload, bytes):
            raise VisualAssetError(f"visual asset payload must be bytes: {name}")
        normalized[name] = payload

    svg_names: set[str] = set()
    png_names: set[str] = set()
    mermaid_names: set[str] = set()
    for name in normalized:
        lowered = name.casefold()
        if lowered.endswith(".png"):
            if not name.endswith("@2x.png"):
                raise VisualAssetError(f"unknown PNG visual asset: {name}")
            png_names.add(name)
        elif lowered.endswith(".svg"):
            if not name.endswith(".svg"):
                raise VisualAssetError(f"unknown visual asset: {name}")
            svg_names.add(name)
        elif lowered.endswith(".mmd"):
            if not name.endswith(".mmd"):
                raise VisualAssetError(f"unknown Mermaid source asset: {name}")
            mermaid_names.add(name)
        elif lowered.endswith(_KNOWN_VISUAL_SUFFIXES):
            raise VisualAssetError(f"unknown visual asset: {name}")

    for png_name in sorted(png_names):
        svg_name = f"{png_name[:-7]}.svg"
        if svg_name not in svg_names:
            raise VisualAssetError(f"orphan PNG pair without SVG: {png_name}")
    if require_png:
        for svg_name in sorted(svg_names):
            png_name = f"{svg_name[:-4]}@2x.png"
            if png_name not in png_names:
                raise VisualAssetError(f"missing PNG pair for SVG: {svg_name}")
    for mermaid_name in sorted(mermaid_names):
        svg_name = f"{mermaid_name[:-4]}.svg"
        if svg_name not in svg_names:
            raise VisualAssetError(
                f"orphan Mermaid source without SVG preview: {mermaid_name}"
            )
        _validate_mermaid_source(mermaid_name, normalized[mermaid_name])
    missing_referenced = sorted(referenced - svg_names)
    if missing_referenced:
        raise VisualAssetError(f"missing reader-visible SVG: {missing_referenced[0]}")

    pairs = [
        _validate_visual_pair_payloads(
            svg_name,
            normalized,
            referenced=svg_name in referenced,
        )
        for svg_name in sorted(svg_names)
    ]
    orphan_pairs = sorted(svg_names - referenced)
    if orphan_pairs:
        raise VisualAssetError(
            f"orphan visual pair is not referenced by Candidate Markdown: {orphan_pairs[0]}"
        )
    return pairs


def _regular_managed_file(root: Path, path: Path, *, label: str) -> Path:
    lexical_root = root.absolute()
    lexical_path = path.absolute()
    root_resolved = lexical_root.resolve()
    if lexical_path.is_symlink() or not lexical_path.is_file():
        raise VisualAssetError(f"{label} must be a regular non-symlink file")
    try:
        resolved = lexical_path.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (OSError, ValueError) as error:
        raise VisualAssetError(f"{label} is outside the managed project") from error
    current = lexical_path
    while current != lexical_root and current != current.parent:
        if current.is_symlink():
            raise VisualAssetError(f"{label} must not traverse symlinks")
        current = current.parent
    return resolved


def _load_managed_visual_payloads(
    project_root: Path, candidate_path: Path
) -> tuple[Path, Path, dict[str, bytes]]:
    """Read one symlink-free managed asset tree for either scan entry point."""
    root = project_root.absolute()
    resolved_root = root.resolve()
    candidate = _regular_managed_file(root, candidate_path, label="Candidate Markdown")
    candidate_tree = candidate.parent
    payloads: dict[str, bytes] = {}
    assets_root = candidate_tree / "assets"
    if assets_root.exists():
        if assets_root.is_symlink() or not assets_root.is_dir():
            raise VisualAssetError(
                "managed visual asset tree must be a regular non-symlink directory"
            )
        for path in sorted(assets_root.rglob("*")):
            if path.is_symlink():
                raise VisualAssetError(
                    "managed visual asset tree entries must be regular non-symlink files"
                )
            if path.is_dir():
                continue
            if not path.is_file():
                raise VisualAssetError(
                    "managed visual asset tree contains a non-regular entry"
                )
            name = path.relative_to(assets_root).as_posix()
            relative = _safe_asset_name(name)
            managed = _regular_managed_file(
                root, assets_root / relative, label=f"managed visual asset {name}"
            )
            try:
                managed.relative_to(assets_root.resolve())
            except ValueError as error:
                raise VisualAssetError(f"unsafe reader-visible asset path: {name}") from error
            payloads[name] = managed.read_bytes()
    return resolved_root, candidate, payloads


def _visual_payload_refs(
    resolved_root: Path, candidate: Path, payloads: Mapping[str, bytes]
) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "path": (candidate.parent / "assets" / name)
            .relative_to(resolved_root)
            .as_posix(),
            "hash": sha256_bytes(payload),
            "version": VISUAL_REF_VERSION,
        }
        for name, payload in payloads.items()
    }


def _bind_validated_visual_pairs(
    raw_pairs: list[dict[str, Any]],
    assets: Mapping[str, bytes],
    asset_refs: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for pair in raw_pairs:
        svg_name = pair["svg_name"]
        png_name = pair["png_name"]
        mermaid_name = pair.get("mermaid_name")
        svg_ref = dict(asset_refs.get(svg_name, {}))
        png_ref = dict(asset_refs.get(png_name, {})) if png_name else None
        mermaid_ref = (
            dict(asset_refs.get(mermaid_name, {})) if mermaid_name else None
        )
        bound = ((svg_name, svg_ref),)
        if png_name:
            bound += ((png_name, png_ref),)
        if mermaid_name:
            bound += ((mermaid_name, mermaid_ref),)
        if any(
            not isinstance(ref, dict)
            or set(ref) != {"path", "hash", "version"}
            or ref["hash"] != sha256_bytes(assets[name])
            for name, ref in bound
        ):
            raise VisualAssetError("visual payload refs are incomplete or stale")
        bound_pair = {"svg_ref": svg_ref, "png_ref": png_ref}
        if mermaid_ref is not None:
            bound_pair["mermaid_source_ref"] = mermaid_ref
        pairs.append(bound_pair)
    return pairs


def inspect_reader_visible_visual_assets(
    project_root: Path, candidate_path: Path
) -> list[dict[str, Any]]:
    """Validate and exact-bind one read of each visible visual source."""

    resolved_root, candidate, payloads = _load_managed_visual_payloads(
        project_root, candidate_path
    )
    try:
        markdown = candidate.read_bytes().decode("utf-8")
    except UnicodeError as error:
        raise VisualAssetError("Candidate Markdown must be UTF-8") from error
    raw_pairs = validate_managed_visual_asset_tree(markdown, payloads)
    return _bind_validated_visual_pairs(
        raw_pairs,
        payloads,
        _visual_payload_refs(resolved_root, candidate, payloads),
    )


def _line_basis_for_spans(
    source: str,
    spans: list[tuple[int, int]],
    *,
    candidate_ref: Mapping[str, Any],
) -> list[dict[str, Any]]:
    bases: list[dict[str, Any]] = []
    for start, end in spans:
        bases.append(
            {
                "path": candidate_ref["path"],
                "hash": candidate_ref["hash"],
                "start_line": source.count("\n", 0, start) + 1,
                "end_line": source.count("\n", 0, max(start, end - 1)) + 1,
            }
        )
    return bases


def _active_visual_spans(source: str) -> list[tuple[int, int]]:
    """Locate active Markdown/HTML visual syntax after literal masking."""

    rendered = _rendered_markdown_source(source)
    spans: list[tuple[int, int]] = []
    for pattern in (
        _INLINE_IMAGE,
        _REFERENCE_IMAGE,
        _SHORTCUT_IMAGE,
        _RAW_IMAGE,
        _RAW_INLINE_SVG,
    ):
        spans.extend(match.span() for match in pattern.finditer(rendered))
    return sorted(set(spans))


def scan_reader_visible_visual_payloads(
    markdown_payload: bytes,
    *,
    candidate_ref: Mapping[str, Any],
    assets: Mapping[str, bytes],
    asset_refs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify an immutable Candidate from content-addressed payloads."""

    if set(candidate_ref) != {"path", "hash", "version"}:
        raise VisualAssetError("visual source scan requires one closed exact Candidate ref")
    if sha256_bytes(markdown_payload) != candidate_ref.get("hash"):
        raise VisualAssetError("visual source scan exact Candidate hash differs")
    try:
        markdown = markdown_payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise VisualAssetError("Candidate Markdown must be UTF-8") from error

    rendered = _rendered_markdown_source(markdown)
    raw_spans = [match.span() for match in _RAW_INLINE_SVG.finditer(rendered)]
    if raw_spans:
        return {
            "schema_version": VISUAL_SOURCE_SCAN_VERSION,
            "status": "REVIEWABLE_UNSAFE_NOT_RENDERED",
            "candidate_access_mode": "SOURCE_TEXT_ONLY",
            "candidate_ref": dict(candidate_ref),
            "issues": [
                {
                    "issue_type": "RAW_INLINE_SVG",
                    "basis_refs": _line_basis_for_spans(
                        markdown, raw_spans, candidate_ref=candidate_ref
                    ),
                    "reason": (
                        "Active raw inline SVG is reviewable only as source text; "
                        "it was not rendered or inspected as a visual."
                    ),
                }
            ],
            "safe_visual_pairs": [],
            "render_status": "NOT_RENDERED",
        }

    try:
        raw_pairs = validate_managed_visual_asset_tree(
            markdown, assets, require_png=False
        )
        safe_pairs = _bind_validated_visual_pairs(raw_pairs, assets, asset_refs)
    except VisualAssetError as error:
        spans = _active_visual_spans(markdown)
        if not spans:
            spans = [(0, min(len(markdown), 1))]
        return {
            "schema_version": VISUAL_SOURCE_SCAN_VERSION,
            "status": "REVIEWABLE_UNSAFE_NOT_RENDERED",
            "candidate_access_mode": "SOURCE_TEXT_ONLY",
            "candidate_ref": dict(candidate_ref),
            "issues": [
                {
                    "issue_type": "UNSAFE_OR_UNAVAILABLE_VISUAL",
                    "basis_refs": _line_basis_for_spans(
                        markdown, spans, candidate_ref=candidate_ref
                    ),
                    "reason": str(error),
                }
            ],
            "safe_visual_pairs": [],
            "render_status": "NOT_RENDERED",
        }
    return {
        "schema_version": VISUAL_SOURCE_SCAN_VERSION,
        "status": "REVIEWABLE_SAFE_NOT_RENDERED",
        "candidate_access_mode": (
            "SOURCE_AND_VALIDATED_VISUALS" if safe_pairs else "SOURCE_TEXT_ONLY"
        ),
        "candidate_ref": dict(candidate_ref),
        "issues": [],
        "safe_visual_pairs": safe_pairs,
        "render_status": "NOT_RENDERED",
    }


def scan_reader_visible_visual_source(
    project_root: Path,
    candidate_path: Path,
    *,
    candidate_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify visuals before any rich-content inspection or rendering.

    Unsafe or unavailable visuals remain reviewable only as exact source text.
    This function deliberately does not call the strict visual inspector when
    active raw inline SVG is present, so active SVG bytes never reach a visual
    consumer during ordinary Review.
    """

    resolved_root, candidate, payloads = _load_managed_visual_payloads(
        project_root, candidate_path
    )
    payload = candidate.read_bytes()
    expected_path = candidate.relative_to(resolved_root).as_posix()
    if candidate_ref.get("path") != expected_path:
        raise VisualAssetError("visual source scan exact Candidate path differs")
    return scan_reader_visible_visual_payloads(
        payload,
        candidate_ref=candidate_ref,
        assets=payloads,
        asset_refs=_visual_payload_refs(resolved_root, candidate, payloads),
    )
