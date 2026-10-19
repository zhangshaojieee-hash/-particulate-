from pathlib import Path
import sys
import types

import pytest

from ai4d.vision_relay import VisionRelayConfigError, call_auto_kinematics_model_via_relay


class _Message:
    content = '{"total_links": 0, "links": [], "joints": []}'


class _Choice:
    message = _Message()


class _Response:
    choices = [_Choice()]


class _Completions:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return _Response()


class _Client:
    last = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.chat = type("Chat", (), {"completions": _Completions()})()
        _Client.last = self


def test_relay_requires_base_url(monkeypatch):
    monkeypatch.delenv("AI4D_VISION_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("AI4D_VISION_API_KEY", "test-key")
    with pytest.raises(VisionRelayConfigError, match="AI4D_VISION_BASE_URL"):
        call_auto_kinematics_model_via_relay(
            model_id="relay-model",
            system_prompt_path=Path(__file__).parents[1] / "README.md",
            rendered_views=[],
        )


def test_relay_builds_multimodal_chat_request(monkeypatch, tmp_path):
    image = tmp_path / "view.png"
    image.write_bytes(b"png-data")
    prompt = tmp_path / "system.txt"
    prompt.write_text("Return JSON.", encoding="utf-8")
    monkeypatch.setenv("AI4D_VISION_BASE_URL", "https://relay.example/v1")
    monkeypatch.setenv("AI4D_VISION_MODEL", "relay-model")
    monkeypatch.setenv("AI4D_VISION_API_KEY", "test-key")

    import ai4d.vision_relay as vision_relay
    monkeypatch.setattr(vision_relay, "OpenAI", _Client)
    official_utils = types.ModuleType("instruct_particulate.utils.auto_kinematics_utils")
    official_utils.build_auto_kinematics_user_prompt = lambda views: "Describe the views."
    official_utils.extract_json_object = lambda content: __import__("json").loads(content)
    monkeypatch.setitem(sys.modules, "instruct_particulate.utils.auto_kinematics_utils", official_utils)

    view = type("View", (), {"image_id": 0, "image_path": image, "width": 1, "height": 1})()
    result = call_auto_kinematics_model_via_relay(
        model_id="ignored-model",
        system_prompt_path=prompt,
        rendered_views=[view],
    )

    assert result["total_links"] == 0
    request = _Client.last.chat.completions.kwargs
    assert request["model"] == "relay-model"
    assert request["messages"][0]["content"] == "Return JSON."
    user_content = request["messages"][1]["content"]
    assert user_content[-1]["type"] == "image_url"
    assert user_content[-1]["image_url"]["url"].startswith("data:image/png;base64,")
