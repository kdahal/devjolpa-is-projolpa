from utils import allowed_file

def test_allowed_file_valid():
    assert allowed_file('test.jpg') == True
    assert allowed_file('test.PNG') == True

def test_allowed_file_invalid():
    assert allowed_file('test.txt') == False
    assert allowed_file('test.exe') == False
    assert allowed_file('') == False