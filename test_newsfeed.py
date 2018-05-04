import unittest
import newsfeed

class TestNewsFeed(unittest.TestCase):

    def test_removehtml(self):
        self.assertEqual('bla', newsfeed.removehtml('<p>bla'))
        self.assertEqual('bla', newsfeed.removehtml('<p>bla</p>'))
        self.assertEqual('>bla<', newsfeed.removehtml('<p>>bla<</p>'))

    def test_topdomain(self):
        # Strips all before the last period.
        self.assertEqual('rolfje.com', newsfeed.topdomain('www.rolfje.com'))
        self.assertEqual('rolfje.com', newsfeed.topdomain('feeds.www.rolfje.com'))
        self.assertEqual('rolfje.com/', newsfeed.topdomain('https://feeds.www.rolfje.com/'))
        self.assertEqual('com/temp.rss', newsfeed.topdomain('https://feeds.www.rolfje.com/temp.rss'))

    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)

if __name__ == '__main__':
    unittest.main()