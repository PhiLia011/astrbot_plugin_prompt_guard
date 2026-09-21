"""人格 / 语言锚定文案生成的测试。"""

from __future__ import annotations

from astrbot_plugin_prompt_guard.pg_anchor import (
    build_language_rule,
    build_persona_anchor,
    build_persona_hardening,
    detect_mixed_language,
    normalize_language,
)


class TestBuildPersonaAnchor:
    def test_basic(self) -> None:
        out = build_persona_anchor("流萤")
        assert "流萤" in out
        assert out.startswith("<persona_anchor>")
        assert out.endswith("</persona_anchor>")

    def test_empty_persona_returns_empty(self) -> None:
        assert build_persona_anchor("") == ""
        assert build_persona_anchor("   ") == ""

    def test_custom_template(self) -> None:
        assert build_persona_anchor("Alice", template="Stay as {persona}!") == (
            "Stay as Alice!"
        )

    def test_broken_template_falls_back(self) -> None:
        out = build_persona_anchor("Bob", template="Stay as {unknown_key}!")
        assert "Bob" in out
        assert out.startswith("<persona_anchor>")


class TestBuildPersonaHardening:
    def test_default(self) -> None:
        assert "跳出角色" in build_persona_hardening()

    def test_with_persona(self) -> None:
        assert "流萤" in build_persona_hardening("流萤")

    def test_custom_line(self) -> None:
        assert build_persona_hardening(line="Be yourself") == "Be yourself"

    def test_empty_line(self) -> None:
        assert build_persona_hardening(line="   ") == ""


class TestNormalizeLanguage:
    def test_known_codes(self) -> None:
        assert normalize_language("zh") == "中文"
        assert normalize_language("EN") == "English"
        assert normalize_language("zh-tw") == "繁體中文"
        assert normalize_language("ja") == "日本語"

    def test_unknown_passthrough(self) -> None:
        assert normalize_language("klingon") == "klingon"

    def test_empty(self) -> None:
        assert normalize_language("") == ""
        assert normalize_language("   ") == ""


class TestBuildLanguageRule:
    def test_basic(self) -> None:
        out = build_language_rule("zh")
        assert "中文" in out
        assert out.startswith("<language_rule>")
        assert out.endswith("</language_rule>")

    def test_accepts_literal_name(self) -> None:
        assert "中文" in build_language_rule("中文")

    def test_empty_returns_empty(self) -> None:
        assert build_language_rule("") == ""
        assert build_language_rule("   ") == ""

    def test_custom_template(self) -> None:
        out = build_language_rule("en", template="Reply in {lang} only.")
        assert out == "Reply in English only."

    def test_broken_template_falls_back(self) -> None:
        out = build_language_rule("en", template="Reply in {oops} only.")
        assert out.startswith("<language_rule>")


class TestDetectMixedLanguage:
    def test_obvious_mix(self) -> None:
        assert detect_mixed_language("这是一个 good idea，我们可以 try 一下") is True

    def test_pure_chinese(self) -> None:
        assert detect_mixed_language("今天天气不错，我们去公园散步吧") is False

    def test_whitelist_proper_nouns(self) -> None:
        assert detect_mixed_language("请帮我看看 GitHub 上的 Python 代码") is False

    def test_whitelist_tech_terms(self) -> None:
        assert detect_mixed_language("这个 bug 出现在 Linux 环境下") is False

    def test_pure_english(self) -> None:
        assert detect_mixed_language("hello world this is english") is False

    def test_empty(self) -> None:
        assert detect_mixed_language("") is False

    def test_too_short_cjk(self) -> None:
        assert detect_mixed_language("ok 好") is False
