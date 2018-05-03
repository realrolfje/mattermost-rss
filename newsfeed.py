#! /usr/bin/python
#
# Scans RSS feeds and sends them to the given mattermost webhook.
#
# Configuration in newsfeed.config looks like:
#
# {
#    "webhook": "https://mattermost.pi9noz.ampr.org/hooks/4ajjzwsdkjb7uewk7w7qn4a4cy",
#    "feeds": [
#        { "feedurl": "https://feeds.agentschaptelecom.nl/nieuws.rss" },
#        {
#            "feedurl": "https://www.rijnmond.nl/rss",
#            "filter": ["radioamateur", "zendamateur", "antenne"]
#        },
# }
#
# The "filter" attribute is optional. If it is present, only posts in the
# rss feed containing the filter words will be posted. If the filter is not
# present, all entries will be posted.
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

def postrssentry(username, entry):
    """
        Posts the entry to mattermost. Returns True if posted
        succesfuly, or False if not.
    """
    payload = {
        'username' : username,
        'text' : "[" + entry.title.encode('utf-8') +"](" 
                    + entry.link.encode('utf-8') + ") "
                    + entry.summary.encode('utf-8')
    }

    # print payload
    # return False
    resp = requests.post(mattermosturl, data=json.dumps(payload))
    return (resp.status_code == 200)

def removehtml(summary):
    stripped = re.sub('<p>Het bericht <a href.+</p>', '', summary)
    stripped = re.sub('<[^<]+?>', '', stripped)
    return stripped

def writeconfig(config):
    """Writes the config to json file"""
    json.dump(config, open(myconfig,'w'))

def readconfig():
    """Reads config from json file"""
    return json.load(open(myconfig))

if __name__ == "__main__":
    # Raw, no checking. Ugly errors when you don't use this script
    # in the form: newsfeed.py <rss link> <mattermost webhook url>

    config = readconfig()
    
    mattermosturl = config['webhook']

    for feed in config['feeds']:
        feedurl = feed['feedurl']
        filter = None
        if  'filter' in feed:
            filter = feed['filter']

        idfile = mydirectory + "/" + urlparse(feedurl).hostname + ".ids"
        postids = readoldpostids(idfile)

        entry = getrssentry(feedurl, postids, filter)

        username = urlparse(feedurl).hostname
        username = re.sub('(^www\\.)|(^feeds\\.)|(^zoek\\.)', '', username)

        if entry is not None and postrssentry(username, entry):
            postids = postids + [entry.id]
            writeoldpostids(idfile, postids)
        else:
            print "No new entry."

