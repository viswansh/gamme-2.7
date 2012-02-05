"""
pyVersion  2.7
google_app version 1.6.2
"""

from __future__ import with_statement

import os

os.environ['BOTO_CONFIG'] = 'boto.cfg'
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import boto
import cgi
import config
import gscloud
import jinja2
import webapp2
import StringIO
import urllib
import utils

from oauth2_plugin import oauth2_plugin
from boto.exception import S3ResponseError
from boto.pyami.config import Config
from google.appengine.api import users, files
from xml.dom.minidom import parseString


### uses Jinja2 for HTML templating ####
jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

### Main Page Request Handler ###
class MainPage(webapp2.RequestHandler):
    def get(self):
        user_id = " "
        template_values = { 'user_text' : user_id }
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))

### Query user ###
class QueryUser(webapp2.RequestHandler):
    def get(self):
        userid = self.request.get('userid')
        ## test for empty userid ##
        if userid.strip() == '':
            errorhandler(self.response,'Empty User ID')
            return

        ## if not status files available ##
        ## TODO check trace files for additional info ##
        result_bunch = gscloud.get_userobjects(userid)
        if len(result_bunch.result) == 0:
            errorhandler(self.response,'User Status files not found')
            return

        stats  = []
        errors = []
        template_values = {'user_name' : userid}
        success = 0
        failed  = 0
        for obj_uri in result_bunch.result:
            dom = parseString(obj_uri.get_contents_as_string())
            user = getText(dom.getElementsByTagName('SourceUser')[0].childNodes)
            if user != userid:
                pass
            #TODO aggregate stats
            main_status = dom.getElementsByTagName('MigrationStatus')[0].getAttribute('value')
            template_values['main_status'] = main_status
            for category in config.Migration_categories:
                d = dom.getElementsByTagName(category + 'MigrationStatus')
                key = category + '_status'
                template_values[key] = d[0].getElementsByTagName('MigrationStatus')[0].getAttribute('value')
                if category == 'Email':
                   bunch = process_email_stats(d[0])
                   success += bunch.success
                   failed  += bunch.failed

        stats.append('Messages Migrated: ' + str(success))
        stats.append('Messages Failed: ' + str(failed))
        stats.append('Percentage Success: ' + str(float((success)/(success+failed))))

            errors.append(('Attachements too large', 'test1'))
            errors.append(('Disallowed File Types', 'test1'))
            errors.append(('others', 'test3'))

            template_values['email_stats']   = stats
            template_values['error_results'] = errors

        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))


## app is thread safe, so all the requests are serialized
## so its, safe to assume the result is always the latest
#class ErrorResultHandler():

def process_email_stats(dom):
    success = 0
    failed  = 0
    for folders in dom.getElementsByTagName('FolderList'):
       success += int(folders.getElementsByTagName('SuccessCount')[0].getAttribute('value'))
       failed += int(folders.getElementsByTagName('FailCount')[0].getAttribute('value'))

    return utils.Bunch(success=success, failed=failed)
        
def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def errorhandler(handler, error):
    error_str = '<span STYLE=\"color: rgb(100%, 0%, 0%)\">' + error + '</span>'
    template_values = { 'error_str' : error_str}
    template = jinja_environment.get_template('index.html')
    handler.out.write(template.render(template_values))

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/queryuser',   QueryUser)],
                                debug=True)
