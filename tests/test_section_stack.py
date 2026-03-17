"""Unit tests for _update_section_stack in block_classifier."""

from __future__ import annotations

from hsc_edu.core.classification.block_classifier import _update_section_stack


def test_push_single_level():
    stack: list[tuple[int, str]] = []
    _update_section_stack(stack, 1, "Chương 1")
    assert stack == [(1, "Chương 1")]


def test_push_nested_levels():
    stack: list[tuple[int, str]] = []
    _update_section_stack(stack, 1, "Chương 1")
    _update_section_stack(stack, 2, "1.1. Mục A")
    _update_section_stack(stack, 3, "1.1.1. Chi tiết")
    assert stack == [
        (1, "Chương 1"),
        (2, "1.1. Mục A"),
        (3, "1.1.1. Chi tiết"),
    ]


def test_pop_same_level():
    stack: list[tuple[int, str]] = []
    _update_section_stack(stack, 1, "Chương 1")
    _update_section_stack(stack, 2, "1.1. Mục A")
    _update_section_stack(stack, 2, "1.2. Mục B")
    assert stack == [(1, "Chương 1"), (2, "1.2. Mục B")]


def test_pop_to_higher_level():
    stack: list[tuple[int, str]] = []
    _update_section_stack(stack, 1, "Chương 1")
    _update_section_stack(stack, 2, "1.1.")
    _update_section_stack(stack, 3, "1.1.1.")
    _update_section_stack(stack, 1, "Chương 2")
    assert stack == [(1, "Chương 2")]


def test_full_sequence():
    """Simulate lv1 -> lv2 -> lv3 -> lv2 -> lv1 -> lv2."""
    stack: list[tuple[int, str]] = []

    _update_section_stack(stack, 1, "Ch1")
    assert [t for _, t in stack] == ["Ch1"]

    _update_section_stack(stack, 2, "1.1")
    assert [t for _, t in stack] == ["Ch1", "1.1"]

    _update_section_stack(stack, 3, "1.1.1")
    assert [t for _, t in stack] == ["Ch1", "1.1", "1.1.1"]

    _update_section_stack(stack, 2, "1.2")
    assert [t for _, t in stack] == ["Ch1", "1.2"]

    _update_section_stack(stack, 1, "Ch2")
    assert [t for _, t in stack] == ["Ch2"]

    _update_section_stack(stack, 2, "2.1")
    assert [t for _, t in stack] == ["Ch2", "2.1"]


def test_empty_stack_push():
    stack: list[tuple[int, str]] = []
    _update_section_stack(stack, 3, "Deep heading")
    assert stack == [(3, "Deep heading")]
