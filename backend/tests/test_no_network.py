"""Prove tests never need the network or a Gemini key."""

from __future__ import annotations

import os
import socket

import pytest

from app.config import Settings
from app.llm.factory import build_llm
from app.llm.fake import FakeLLM


def test_opening_a_real_socket_raises():
    with pytest.raises(Exception):
        socket.create_connection(("1.1.1.1", 80), timeout=0.1)


def test_gemini_api_key_is_absent():
    assert os.environ.get("GEMINI_API_KEY") in (None, "")


def test_build_llm_returns_fake_when_provider_is_fake():
    settings = Settings(llm_provider="fake", gemini_api_key="", gemini_model="gemini-3.8-flash")
    llm = build_llm(settings)
    assert isinstance(llm, FakeLLM)


def test_build_llm_returns_fake_for_auto_without_key():
    settings = Settings(llm_provider="auto", gemini_api_key="", gemini_model="gemini-3.8-flash")
    llm = build_llm(settings)
    assert isinstance(llm, FakeLLM)
