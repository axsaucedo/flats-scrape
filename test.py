from main import WunderManager
import os

FILE_INJECT = "flats-test.json"

def test_fetch_new():
    wm = WunderManager()
    listings = wm._fetch_new()
    assert listings

def test_workflow():
    wm = WunderManager()
    body = wm.process()
    assert body

def test_no_file():
    try:
        wm = WunderManager(save_file="DOESNOTEXIST")
        body = wm.process()
        assert body
        wm.save_new()
        assert os.path.isfile("DOESNOTEXIST")
    finally:
        os.remove("DOESNOTEXIST")


