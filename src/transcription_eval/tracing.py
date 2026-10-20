"""Opt-in telemetry and runtime-only credentials; never include keys in metadata."""

import os
import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


def load_credentials(path: Path | None = None):
    """Read only credentials from a user-selected text file, not executable instructions.

    Existing environment values take precedence. No secret values are returned.
    """
    path = path or (
        Path(os.environ["MEETING_CREDENTIALS_FILE"])
        if os.getenv("MEETING_CREDENTIALS_FILE")
        else None
    )
    if path is None:
        return
    if path.suffix.lower() == ".docx":
        with ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        # Preserve run joins while separating paragraphs; never execute document text.
        content = "\n".join("".join(p.itertext()) for p in root.iter(namespace + "p"))
    else:
        content = path.read_text(encoding="utf-8-sig")
    patterns = {
        "LANGFUSE_PUBLIC_KEY": r"\bpk-lf-[A-Za-z0-9_-]+",
        "LANGFUSE_SECRET_KEY": r"\bsk-lf-[A-Za-z0-9_-]+",
        "OPENAI_API_KEY": r"\bsk-(?!lf-)[A-Za-z0-9_-]{20,}",
    }
    for name, pattern in patterns.items():
        matches = set(re.findall(pattern, content))
        if len(matches) > 1:
            raise ValueError(
                f"Multiple {name} credentials found; use an explicit environment value"
            )
        if matches:
            os.environ.setdefault(name, matches.pop())
    # Limit automatic host extraction to known Langfuse cloud hosts. Self-hosted
    # deployments must supply LANGFUSE_BASE_URL explicitly in the environment.
    hosts = re.findall(r"https://(?:us\.|jp\.)?cloud\.langfuse\.com\b", content)
    if hosts:
        os.environ.setdefault("LANGFUSE_BASE_URL", hosts[0])


def client():
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        if not os.getenv(name):
            raise ValueError(f"Missing {name}; configure credentials before enabling tracing")
    from langfuse import get_client

    return get_client()
