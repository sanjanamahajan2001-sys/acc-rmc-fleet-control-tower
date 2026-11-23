"""
Unit tests for Pagination DTOs
"""

from app.repositories.pagination import Page, PageRequest


def test_page_request_offset_calculation():
    req = PageRequest(page=1, size=20)
    assert req.offset == 0

    req_p3 = PageRequest(page=3, size=50)
    assert req_p3.offset == 100


def test_page_envelope_metadata_calculation():
    req = PageRequest(page=2, size=10)
    items = ["item1", "item2"]
    page_data = Page.create(items=items, total_elements=25, page_request=req)

    assert page_data.total_elements == 25
    assert page_data.total_pages == 3
    assert page_data.has_next is True
    assert page_data.has_previous is True
