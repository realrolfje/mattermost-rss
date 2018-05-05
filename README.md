# mattermost-rss

Send RSS feeds to a Mattermost Webhook.

This script allows you to have a channel "news" in your Mattermost installation, and fill it with the RSS feeds of news sources, optionally filtered for specific words/topics.

## Simplest configuration:

Put the `newsfeed.py` and `newsfeed.config` file in the same directory of your choosing.
The minimal configuration file you need looks like this (replace urls with your own):

```
{
    "webhook": "https://your.mattermost.org/hooks/<yourwebhook>",
    "feeds": [
        {
            "feedurl": "http://rsgb.org/feed/"
        }
    ]
}
```

This configuration will post all news entries from rsgb.org to the supplied webhook.

## Advanced configuration:

To make it more interesting, you can add more RSS feeds, have a custom username,
and even filter on certain words to filter on. See
[the example configuration](newsfeed.config) for an example of all the fields you
can use and how to use them.