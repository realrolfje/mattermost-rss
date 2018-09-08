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
import time
from urlparse import urlparse, parse_qs

mydirectory = os.path.dirname(os.path.realpath(__file__))
myconfig = mydirectory + "/newsfeed.config"


def readoldpostids(idfile):
    """
        Loads already processed ids from file.
    """
    try:
        text_file = open(idfile, "r")
        postids = json.loads(text_file.read())
        text_file.close()
    except IOError:
        print "No ids file " + idfile + " , start with empty list."
        postids = []
        writeoldpostids(idfile, postids)

    return postids


def writeoldpostids(idfile, postids):
    """
        Writes processed ids to file
    """
    try:
        text_file = open(idfile, "w")
        text_file.write(json.dumps(postids))
        text_file.close()
    except IOError as e:
        print "ERROR: Can not write " + idfile + "."
        print e


def containsanyword(filter, entry):
    if filter is None:
        return True

    for word in filter:
        if word.lower() in entry.title.lower() or word.lower() in entry.summary.lower():
            return True

    return False


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
            entry.summary = removehtml(entry.summary)
            filtered += {entry}

    return filtered

def buildmattermostpayload(username, entry):
    """
        Transforms the rss entry into a payload which
        can be sent to mattermost. Payload will be
        different depending on the contents of the entry
        so that it will be correctly rendered by
        mattermost.
    """
    if 'twitter_place' in entry:
        # Support for entries from https://twitrss.me
        return {
            'username': username,
            'text': "[tweet:]("
            + entry.link.encode('utf-8') + ") "
            + entry.title.encode('utf-8')
        }
    else:
        return {
            'username': username,
            'text': "[" + entry.title.encode('utf-8') + "]("
            + entry.link.encode('utf-8') + ") "
            + entry.summary.encode('utf-8')
        }

def postrssentry(mattermosturl, username, entry):
    """
        Posts the entry to mattermost. Returns True if posted
        succesfuly, or False if not.
    """
    payload = buildmattermostpayload(username, entry)

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

    config = json.loads(cleanconfig)

    # Cleanup and defaults so we have a valid configuration
    for feed in config['feeds']:
        if 'username' not in feed:
            feed['username'] = topdomain(urlparse(feed['feedurl']).hostname)

        if 'include' not in feed: feed['include'] = None
        if 'exclude' not in feed: feed['exclude'] = None

    return config

def idfilefromurl(url):
    parsedurl = urlparse(url)
    query = parse_qs(parsedurl.query, keep_blank_values=True)

    if parsedurl.hostname == 'twitrss.me':
        idfile = mydirectory + "/" + parsedurl.hostname + "." + query['user'][0]+ ".ids"
    else:
        idfile = mydirectory + "/" + parsedurl.hostname + ".ids"
    return idfile


if __name__ == "__main__":
    start = time.time()

    # Raw, no checking. Ugly errors when you don't use this script
    # in the form: newsfeed.py <rss link> <mattermost webhook url>
    config = readconfig()

    for feed in config['feeds']:

        idfile = idfilefromurl(feed['feedurl'])
        oldpostids = readoldpostids(idfile)

        entries = getnewrssentries(feed['feedurl'], oldpostids)
        entries = filterrssentries(entries, feed['include'], feed['exclude'])

        if len(entries) > 0:
            entry = entries[0]
        else:
            print "No new entry for " + feed['feedurl'] + "."
            continue

        # Support for global and local webhooks
        webhooks=[]
        if 'webhook' in feed:
            webhooks = feed['webhook']
        elif 'webhook' in config:
            webhooks = config['webhook']
        else:
            # Print the entry and skip actual posting.
            print "No webhook defined. Would have posted '" + entry.title + "' as '" + feed['username'] + "'."
            continue

        # Support for multiple webhooks in an array.
        if not isinstance(webhooks, list):
            webhooks = [webhooks]

        posted = False

        for webhook in webhooks:
            if 'post' in feed and feed['post'] == "False":
                print "Not posting entry: " + entry.title
                posted = True
            elif postrssentry(webhook, feed['username'], entry):
                posted = True
            else:
                print "Failed to post entry:"
                print entry
                posted = False

            if posted and entry.id not in oldpostids:
                oldpostids = oldpostids + [entry.id]
                writeoldpostids(idfile, oldpostids)

    end = time.time()
    elapsed = str(round(end - start, 1))
    print "Total time: " + elapsed + " seconds."


