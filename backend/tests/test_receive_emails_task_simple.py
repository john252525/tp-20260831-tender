import pytest
from app.workers.tasks import normalize_message_id

def test_normalize_message_id():
    assert normalize_message_id('<abc@example.com>') == 'abc@example.com'
    assert normalize_message_id('  <abc@example.com>  ') == 'abc@example.com'
    assert normalize_message_id('abc@example.com') == 'abc@example.com'
    assert normalize_message_id('') == ''
