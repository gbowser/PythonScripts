import pytest

@pytest.fixture(autouse=True)
def isolate_saved_account_allocation(tmp_path,monkeypatch):
    import account_allocation
    monkeypatch.setattr(account_allocation,'ALLOCATION',tmp_path/'account_allocation.json')
