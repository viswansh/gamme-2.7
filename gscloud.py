
import os

os.environ['BOTO_CONFIG'] = 'boto.cfg'
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import boto
import config
import logging
import re
import utils

from oauth2_plugin import oauth2_plugin
from boto.exception import S3ResponseError
from boto.pyami.config import Config


def get_userobjects(filter=None):
    objects   = []
    error_str = ''
    pattern   = None
    if filter != None:
        pattern=r'Status-' + filter + '-(.*)-p(.*).log'
    else:
        pattern=None
    try:
        ## get all the buckets under the storage with the given key id ##
        if len(config.BUCKETS) == 0:
            uri     = boto.storage_uri('', config.GOOGLE_STORAGE)
            buckets = [bucket.name for bucket in uri.get_all_buckets()]
        else:
            buckets = config.BUCKETS
        ## list of objects ##
        for bucket in buckets:
            uri = boto.storage_uri(bucket, config.GOOGLE_STORAGE)
            for obj_uri in uri.get_bucket():
                if pattern != None:
                    if re.match(pattern, obj_uri.name) != None:
                        objects.append('%s://%s/%s' % (uri.scheme, uri.bucket_name, obj_uri.name))
                else:
                    objects.append('%s://%s/%s' % (uri.scheme, uri.bucket_name, obj_uri.name))
    except AttributeError, e:
        objects = None
        error_str = 'GSCloud::get_userlist Attribute Error %s'% (e)
        logging.error(error_str)
    except S3ResponseError, e:
        objects = None
        error_str = 'GSCloud::get_userlist Response Error status=%d,code=%s, reason=%s.</b>' % (e.status, e.code, e.reason)
        logging.error(error_str)

    return utils.Bunch(result=objects, 
                       error=error_str)
