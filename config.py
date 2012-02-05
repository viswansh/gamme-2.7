"""
pyVersion 2.7
"""

Google_storage='gs'
Buckets = []

##just in case there are multiple runs
##aggregation follows below priority for status
Status_priority = ['Failed', 'In Progress', 'Completed']
Status_log_pattern='Status-%s-(.*)-p(.*).log'

Migration_categories = ['Calendar', 'Contact', 'Email']


