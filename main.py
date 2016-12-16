import functools
import logging
import json
import urllib
import re
#from operator import itemgetter
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import time
import webapp2

localtime = time.asctime( time.localtime(time.time()) )


def getBlobid(searchstr):
    #first we call PubMed and scrape the blobid off the page
    urlstem = "https://www.ncbi.nlm.nih.gov/pubmed/?term="
    url = urlstem + searchstr
    try:
        validate_certificate = 'true'
        result = urlfetch.fetch(url)
        if result.status_code == 200:
            myText = result.content
            m = re.search('blobid=(.*):yr=', myText)
            if m:
                blobId = m.group(1)
                #newResponse = fetchCsv(blobId, searchstr)
                return blobId
            else:
                return "Too few results!"
        else:
            return result.status_code
    except urlfetch.Error:
        logging.exception('Caught exception fetching url')


def fetchCsv(blobId, searchstr):
    #now we take that blobid and request the CSV
    csvstem = "https://www.ncbi.nlm.nih.gov/pubmed?p$l=Email&Mode=download&dlid=timeline&filename=timeline.csv"
    try:
        validate_certificate = 'true'
        csvurl = csvstem + "&term=" + searchstr + "&bbid=" + blobId + "&p$debugoutput=off"
        result = urlfetch.fetch(csvurl)
        if result.status_code == 200:
            yearCounts = {
                "timestamp": localtime,
                "search": searchstr,
                "counts": {}
            }
            myText = (result.content).splitlines()
            myText.pop(0)
            myText.pop(0)
            myText.pop()
            for l in myText:
                l = l.split(',')
                year = l.pop(0)
                count = l.pop(0)
                yearCounts['counts'][year] = count
                    #yearcount = {
                    #    "year": year,
                    #    "count": count,
                    #}
                    #yearCounts['counts'].append(yearcount)

        else:
            return result.status_code
    except urlfetch.Error:
            logging.exception('Caught exception fetching url')

        #yearCounts['counts'] = sorted(yearCounts['counts'], key=itemgetter('year'))
    prettiness = json.dumps(yearCounts, sort_keys=True, indent=4)
    return prettiness

class myJson(ndb.Model):
    applicationName = ndb.StringProperty()
    json = ndb.TextProperty()

class getCounts(webapp2.RequestHandler):
    def get(self):
        query = self.request.get('q')
        searchstr = urllib.quote_plus(query)
        myBlobid = getBlobid(searchstr)
        if myBlobid == "Too few results!":
            thisJson = json.dumps({ 'error': 'None or too few results' })
        else:
            thisJson = fetchCsv(myBlobid, searchstr)
        self.response.headers = { "Content-Type": "application/json; charset=UTF-8",
         "Access-Control-Allow-Origin": "*" }
        self.response.write(thisJson)

class BuildBaseCounts(webapp2.RequestHandler):
    def get(self):
        searchstr = "all[sb]"
        myBlobid = getBlobid(searchstr)
        thisJson = fetchCsv(myBlobid, searchstr)
        self.response.write(thisJson)

        gotJson = myJson.query(myJson.applicationName=='medtime').fetch()
        if len(gotJson) > 0:
            baseline = gotJson[0]
            baseline.json = thisJson
            baseline.put()
        else:
            baselinejson = myJson(applicationName='medtime', json=thisJson)
            baselinejson.put()

class ShowBaseCounts(webapp2.RequestHandler):
    def get(self):
        self.response.headers = { "Content-Type": "application/json; charset=UTF-8",
         "Access-Control-Allow-Origin": "*" }
        latestJson = myJson.query(myJson.applicationName=='medtime').get()
        self.response.write(latestJson.json)

app = webapp2.WSGIApplication([
    ('/search', getCounts),
    ('/buildbasecounts', BuildBaseCounts),
    ('/showbasecounts', ShowBaseCounts),
], debug=True)
