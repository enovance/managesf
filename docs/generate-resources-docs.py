#!/usr/bin/env python

from mock import patch, MagicMock

m_mock = MagicMock()
modules = {'managesf.services.gerrit': m_mock}
m_patcher = patch.dict('sys.modules', modules)
m_patcher.start()
from managesf.model.yamlbkd.resources.gitrepository import GitRepository
from managesf.model.yamlbkd.resources.project import Project
from managesf.model.yamlbkd.resources.gitacls import ACL
from managesf.model.yamlbkd.resources.group import Group


def render_resource(cls):
    print
    print cls.MODEL_TYPE
    print "-"*len(cls.MODEL_TYPE)
    print
    for key, details in cls.MODEL.items():
        print
        print key
        print "^"*len(key)
        print "* Description: %s" % details[5]
        print "* Type: %s" % str(details[0])
        print "* Authorized value: RE(%s)" % details[1]
        print "* Mandatory key: %s" % details[2]
        print "* Mutable key: %s" % details[4]
        if not details[2]:
            print "* Default value: %s" % details[3]

if __name__ == '__main__':
    print "Available resources models"
    print "=========================="
    for cls in (Project, ACL, GitRepository, Group):
        render_resource(cls)
