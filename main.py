import sys
sys.path.insert(0, "libs")

import functools
import logging
import json
from bs4 import BeautifulSoup
import urllib
import re
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import time
import webapp2

localtime = time.asctime( time.localtime(time.time()) )


def fetchNewCounts(searchstr):
    urlfetch.set_default_fetch_deadline(60)
    labstem = "https://pubmed.ncbi.nlm.nih.gov/?term="
    url = labstem + searchstr
    try:
        validate_certificate = 'true'
        result = urlfetch.fetch(url)
        if result.status_code == 200:
            yearCounts = {
                "timestamp": localtime,
                "search": searchstr,
                "counts": {}
            }
            myText = (result.content)
            lab_html = BeautifulSoup(myText, "html.parser")
            if lab_html.select('#timeline-table'):
                yeartable = lab_html.select('#timeline-table')[0]
                yeartable_body = yeartable.find('tbody')
                rowcount = 0
                for row in yeartable_body.findAll("tr"):
                    cells = row.findAll("td")
                    year = cells[0].find(text=True).strip()
                    count = cells[1].find(text=True).strip()
                    yearCounts['counts'][year] = count
            else:
                yeartable = ""
        else:
            return result.content
    except urlfetch.Error:
        logging.exception('Caught exception fetching url')
    if yeartable:
        prettiness = json.dumps(yearCounts, sort_keys=True, indent=4)
    else:
        prettiness = json.dumps({ 'error': 'None or too few results' })
    return prettiness

class myJson(ndb.Model):
    applicationName = ndb.StringProperty()
    json = ndb.TextProperty()

class getNewCounts(webapp2.RequestHandler):
    def get(self):
        self.response.headers = { "Content-Type": "application/json; charset=UTF-8",
         "Access-Control-Allow-Origin": "*" }
        query = self.request.get('q')
        searchstr = urllib.quote_plus(query)
        myResponse = fetchNewCounts(searchstr)
        self.response.write(myResponse)

class BuildNewBaseCounts(webapp2.RequestHandler):
    def get(self):
        searchstr = "all[sb]"
        thisJson = fetchNewCounts(searchstr)
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
    ('/newsearch', getNewCounts),
    ('/buildnewbasecounts', BuildNewBaseCounts),
    ('/showbasecounts', ShowBaseCounts),
], debug=True)
