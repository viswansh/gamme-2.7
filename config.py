"""
pyVersion 2.7
"""

Google_storage='gs'
Buckets = []

##In case there are multiple runs then
##aggregation follows below priority for status
##ie., if 1st run is completed but second is Failed,overall status is failed
Status_priority = ['Failed', 'In Progress', 'Completed']
Status_log_pattern='Status-%s-(.*)-p(.*).log'

Migration_categories = ['Calendar', 'Contact', 'Email']


