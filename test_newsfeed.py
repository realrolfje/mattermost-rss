import unittest
import newsfeed
import feedparser


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

    def createentry(self, id, title, summary):
        e = feedparser.FeedParserDict()
        e['id'] = id
        e['title'] = title
        e['summary'] = summary
        print e
        return e

    def test_filterrssentries(self):
        entries = feedparser.parse(
            """<?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
                <channel>
                    <item>
                        <title>Brilliant Title</title>
                        <link>https://link-to-article.com/article1</link>

                        <guid isPermaLink="false">https://link-to-article.com/article1</guid>
                        <description><![CDATA[I can include cheeseburger.]]]></description>
                    </item>
                    <item>
                        <title>Dumb Title</title>
                        <link>https://link-to-article.com/article2</link>

                        <guid isPermaLink="false">https://link-to-article.com/article1</guid>
                        <description><![CDATA[I think this needs to be excluded.]]]></description>
                    </item>
                </channel>
            </rss>"""
        ).entries

        filtered = newsfeed.filterrssentries(entries, None, None)
        self.assertEqual(2, len(filtered), msg="Should not filter anything.")

        filtered = newsfeed.filterrssentries(entries, ['Brilliant'], None)
        self.assertEqual(1, len(filtered), msg="Include on title filter failed.")
        self.assertEqual("Brilliant Title", filtered[0].title)

        filtered = newsfeed.filterrssentries(entries, ['include'], None)
        self.assertEqual(1, len(filtered), msg="Include on summary filter failed.")
        self.assertEqual("Brilliant Title", filtered[0].title)

        filtered = newsfeed.filterrssentries(entries, None, ['dUmB'])
        self.assertEqual(1, len(filtered), msg="Exclude on title filter failed.")
        self.assertEqual("Brilliant Title", filtered[0].title)

        filtered = newsfeed.filterrssentries(entries, None, ['exclude'])
        self.assertEqual(1, len(filtered), msg="Exclude on partial word in summary filter failed.")
        self.assertEqual("Brilliant Title", filtered[0].title)

        filtered = newsfeed.filterrssentries(entries, ['excluded'], ['excluded'])
        self.assertEqual(0, len(filtered), msg="Exclude should always exclude, even if in included filter.")


    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)


if __name__ == '__main__':
    unittest.main()
