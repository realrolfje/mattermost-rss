#! /usr/bin/python
#
# Scans RSS feeds and sends them to the given mattermost webhook.
#
# See newsfeed.config for comments and how to configure.
#
# Ids of posts which have already been posted are stored in files with
# the same name as the hostname, with extension "ids".
#
# If rss feeds do not contain ids, this script will calculate a hash based
# on the link url of the article and use that is id.
#
# Prerequisits:
# sudo pip install feedparser
#

import feedparser
import socket
import json
import requests
import os
import sys
import re
import json
from urlparse import urlparse

mydirectory = os.path.dirname(os.path.realpath(__file__))
myconfig = mydirectory + "/newsfeed.config"


def readoldpostids(idfile):
    """
        Loads already processed ids from file.
    """

    # load ids already parsed
    try:
        text_file = open(idfile, "r")
        postids = json.loads(text_file.read())
        text_file.close()
    except IOError:
        print "no ids file, start with empty list."
        postids = []
    return postids


def writeoldpostids(idfile, postids):
    """
        Writes processed ids to file
    """
    text_file = open(idfile, "w")
    text_file.write(json.dumps(postids))
    text_file.close()


def containsanyword(filter, entry):
    if filter is None:
        return True

    for word in filter:
        if word.lower() in entry.title.lower() or word.lower() in entry.summary.lower():
            return True

    return False


def getrssentry(feedurl, oldpostids, filter):
    """
        Loads rss entries from feedurl, and returns
        the one feed that is not in postids
    """

    socket.setdefaulttimeout(120)

    # Load the rss feed
    print "Loading: " + feedurl
    rssentries = feedparser.parse(feedurl).entries

    # Find the oldest post that is new to us.
    for entry in rssentries:

        if 'id' not in entry:
            # No id, generating hash based on link url.
            entry.id = abs(hash(entry.link)) % (10 ** 8)

        # Not posted earlier and contains the right words?
        if entry.id not in postids and containsanyword(filter, entry):
            entry.summary = removehtml(entry.summary)
            return entry

    # No new entry found, return none.
    return None


def getnewrssentries(feedurl, oldpostids):
    """
        Loads rss entries from feedurl, and returns
        the one feed that is not in postids
    """
    socket.setdefaulttimeout(120)
    rssentries = feedparser.parse(feedurl).entries
    newentries = []

    # Find the oldest post that is new to us.
    for entry in rssentries:

        if 'id' not in entry:
            # No id, generating hash based on link url.
            entry.id = abs(hash(entry.link)) % (10 ** 8)

        # Not posted earlier and contains the right words?
        if entry.id not in oldpostids:
            newentries += [entry]

    return newentries


def filterrssentries(entries, include, exclude):
    """
        Returns a new set of entries, only those that
        contain the words in the "include" array and
        do not contain the words in the "exclude" array.
    """
    filtered = []
    for entry in entries:
        if (
            (include is None or containsanyword(include, entry))
            and not
            (exclude is not None and containsanyword(exclude, entry))
        ):
            filtered += {entry}

    return filtered


def postrssentry(mattermosturl, username, entry):
    """
        Posts the entry to mattermost. Returns True if posted
        succesfuly, or False if not.
    """
    payload = {
        'username': username,
        'text': "[" + entry.title.encode('utf-8') + "]("
        + entry.link.encode('utf-8') + ") "
        + entry.summary.encode('utf-8')
    }

    try:
        resp = requests.post(mattermosturl, data=json.dumps(payload))
        return (resp.status_code == 200)
    except:
        print "Failed to post to " + mattermosturl
        return False


def removehtml(summary):
    stripped = re.sub('<p>Het bericht <a href.+</p>', '', summary)
    stripped = re.sub('<[^<]+?>', '', stripped)
    return stripped


def topdomain(hostname):
    while hostname.count('.') > 1:
        # Matches characters up to the first "."
        hostname = re.sub(r'^(.+?)\.', '', hostname)

    return hostname


def writeconfig(config):
    """Writes the config to json file"""
    json.dump(config, open(myconfig, 'w'))


def readconfig():
    """Reads config from json file"""

    cleanconfig = ""
    with open(myconfig) as f:
        content = f.readlines()
        content = [re.sub('#.*', '', x) for x in content]

        cleanconfig = "".join(content)

    return json.loads(cleanconfig)


if __name__ == "__main__":
    # Raw, no checking. Ugly errors when you don't use this script
    # in the form: newsfeed.py <rss link> <mattermost webhook url>

    config = readconfig()

    if 'webhook' in config:
        mattermosturl = config['webhook']
    else:
        mattermosturl = None

    for feed in config['feeds']:
        feedurl = feed['feedurl']

        includewords = None
        if 'include' in feed:
            includewords = feed['include']

        excludewords = None
        if 'exclude' in feed:
            excludewords = feed['exclude']

        idfile = mydirectory + "/" + urlparse(feedurl).hostname + ".ids"
        oldpostids = readoldpostids(idfile)

        entries = getnewrssentries(feedurl, oldpostids)
        entries = filterrssentries(entries, includewords, excludewords)
        entry = entries[0]

        username = topdomain(urlparse(feedurl).hostname)

        if 'webhook' not in config:
            # Print the entry and skip actual posting.
            print "No webhook defined. The following entry would have been posted:"
            print entry
            continue

        if entry is not None and postrssentry(config['webhook'], username, entry):
            postids = postids + [entry.id]
            writeoldpostids(idfile, postids)
        else:
            print "No new entry."
