from main import WunderManager

FILE_INJECT = "flats-test.json"

def test_fetch_new():
    wm = WunderManager()
    listings = wm._fetch_new()
    assert listings

def test_workflow():
    wm = WunderManager()
    body = wm.process()
    assert body



