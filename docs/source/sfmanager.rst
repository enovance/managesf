.. toctree::

sfmanager
=========

This documentation describes the shell utility **sfmanager**, which is a CLI for
the managesf REST API interface in Software Factory. It can be used to
administrate Software Factory, for example to manage projects and users.

Introduction
------------

By default all actions require authentication as well as some information about
the server (URL of the authentication and managesf backends; might be the same).
For example:

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password

Help is always available using the argument '-h':

.. code-block:: bash

 sfmanager create -h
 usage: sfmanager create [-h] --name [project-name]
                         [--description [project-description]]
 ...

.. _managesf_create_project:

Project management
------------------

Create new project
''''''''''''''''''

SF exposes ways to create and initialize projects in Redmine and Gerrit
simultaneously. Initializing a project involves setting up the ACL and
initializing the source repository.

Any user that can authenticate against SF will be able to create a project.

SF allows you to create projects in one of the following ways.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           create --name <project-name>

Delete Project
''''''''''''''

SF exposes ways to delete projects and the groups associated with the project in
Redmine and Gerrit simultaneously.

For any project, only the PTLs shall have the permission to delete it.

SF allows you to delete projects in one of the following ways.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           delete --name <project-name>


User management
---------------

Add user to project groups
''''''''''''''''''''''''''

SF exposes ways to add user to specified groups associated to a project in
Redmine and Gerrit simultaneously.

If the caller user is in the PTL group of the project then the user can add user
in any groups.

If the caller user is in the core user groups of the project then the user can:

* Add user to the core group
* Add user to the dev group

If the caller user is in the dev user groups or even not in any groups related
to that project then the user cannot add users in any groups.

SF allows you to add user in groups in one of the following way.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           add_user --name user1 --groups p1-ptl,p1-core


Remove user from project groups
'''''''''''''''''''''''''''''''

SF exposes ways to remove user from specified or all groups associated to a
project in Redmine and Gerrit simultaneously.

If the caller user is in the PTL group of the project then the user can remove
user in any groups.

If the caller user is in the core user groups of the project then the user can:

* Remove user to the core group
* Remove user to the dev group

If the caller user is in the dev user groups or even not in any groups related
to that project then the user cannot remove users in any groups.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           delete_user --name user1 --group p1-ptl


If the request does not provide a specific group to delete the user from, SF
will remove the user from all group associated to a project.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           delete_user --name user1


Remote replication mangement
----------------------------

 # To be filled

Backup and restore
------------------

Create a new backup
'''''''''''''''''''

SF exposes ways to perform and retrieve a backup of all the user data store in
your SF installation. This backup can be used in case of disaster to quickly
recover user data on the same or other SF installation (in the same version).

Only the SF administrator can perform and retrieve a backup.

SF allows you to perform a backup in one of the following way.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           backup_get

A file called "sf_backup.tar.gz" will be created in the local directory.


Restore a backup
''''''''''''''''

SF exposes ways to restore a backup of all the user data store in your
SF installation. This backup can be used in case of disaster to quickly
recover user data on the same or other SF installation (in the same version).

Only the SF administrator can restore a backup.

SF allows you to restore a backup in one of the following way.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           restore --filename sf_backup.tar.gz
