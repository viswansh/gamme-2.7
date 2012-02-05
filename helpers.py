
"""
small utility class to reference  
elements using . notation
"""
class Bunch(object):
    def __init__(self, **kwds):
        self.__dict__ = kwds

    def __setitem__(self, key, val):
        self.__dict__[key] = val

    def __getitem__(self, key):
        if key in  self.__dict__:
            return self.__dict__[key]
        return None

"""returns data for all node types == TEXT_NODE"""
def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

"""returns the attribute of the first node match tag_name"""
def getTopAttribute(dom, tag_name, attribute_name):
    elems = dom.getElementsByTagName(tag_name)
    if len(elems) == 0:
        return ''
    else:
        return elems[0].getAttribute(attribute_name)

"""returns text of the first node matching tab_name"""
def getTopText(dom, tag_name):
    elems = dom.getElementsByTagName(tag_name)
    if len(elems) == 0:
        return ''
    else:
        return getText(elems[0].childNodes)


"""
highest priority is index 0
if the new value has higher priority then insert else discard
"""
def insert_with_priority(dict, key, val, priority_list):
    if key not in dict:
        dict[key] = val
    else:
        if priority_list.index(dict[key]) > priority_list.index(val):
            dict[key] = val
