from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

from openai import OpenAI


class VisionRelayConfigError(RuntimeError):
    """Raised when the relay configuration is incomplete."""


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise VisionRelayConfigError(f"Missing required environment variable: {name}")
    return value


def _image_data_url(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
        return "".join(str(part) for part in text_parts)
    return str(content or "")


def call_auto_kinematics_model_via_relay(
    *,
    model_id: str,
    system_prompt_path: Path,
    rendered_views: Sequence[Any],
    provider: str | None = None,
    api_key: str | None = None,
    reasoning_effort: str = "medium",
) -> dict[str, Any]:
    """Call a relay's OpenAI-compatible vision endpoint for auto-kinematics.

    The official app supplies rendered views and a JSON schema prompt. This
    function changes only the transport: it sends the same task through
    ``/v1/chat/completions`` and returns a parsed JSON object to the official
    parser. API keys are read from the environment and never logged.
    """
    del provider, reasoning_effort
    base_url = os.environ.get("AI4D_VISION_BASE_URL", "").strip()
    if not base_url:
        base_url = os.environ.get("OPENAI_BASE_URL", "").strip()
    if not base_url:
        raise VisionRelayConfigError(
            "Set AI4D_VISION_BASE_URL to the relay /v1 base URL."
        )

    configured_model = os.environ.get("AI4D_VISION_MODEL", "").strip() or str(model_id)
    configured_key = api_key or os.environ.get("AI4D_VISION_API_KEY", "").strip()
    if not configured_key:
        configured_key = (
            os.environ.get("OPENAI_API_KEY", "").strip()
            or os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY", "").strip()
        )
    if not configured_key:
        raise VisionRelayConfigError(
            "Set AI4D_VISION_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY."
        )

    system_prompt = system_prompt_path.read_text(encoding="utf-8").strip()
    from instruct_particulate.utils.auto_kinematics_utils import (
        build_auto_kinematics_user_prompt,
        extract_json_object,
    )

    user_prompt = build_auto_kinematics_user_prompt(rendered_views)
    user_content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
    for view in rendered_views:
        user_content.append(
            {
                "type": "text",
                "text": (
                    f"Image ID {view.image_id}: the next image corresponds to this ID. "
                    "Use this integer in point_prompt.image_id."
                ),
            }
        )
        user_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": _image_data_url(Path(view.image_path)),
                    "detail": "high",
                },
            }
        )

    client = OpenAI(api_key=configured_key, base_url=base_url.rstrip("/"))
    response = client.chat.completions.create(
        model=configured_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
    )
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise RuntimeError("Vision relay returned no choices.")
    message = getattr(choices[0], "message", None)
    content = _content_text(getattr(message, "content", None))
    if not content:
        raise RuntimeError("Vision relay returned empty message content.")

    host = urlsplit(base_url).netloc or base_url
    print(
        f"AI4D vision relay response received: host={host}, "
        f"model={configured_model}, views={len(rendered_views)}"
    )
    return extract_json_object(content)
