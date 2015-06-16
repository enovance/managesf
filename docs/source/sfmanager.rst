.. toctree::

sfmanager
=========

This documentation describes the shell utility **sfmanager**, which is a CLI for
the managesf REST API interface in Software Factory. It can be used to
administrate Software Factory, for example to manage projects and users.

Introduction
------------

Global options
''''''''''''''

By default all actions require authentication as well as some information about
the remote servers.

--url <http://sfgateway.dom>
    URL of the managesf instance

--auth-server-url <http://sfgateway.dom>
    URL of the authentication server, can be the same as the managesf URL

--auth user:password
    Username and password to use when accessing the managesf interface. This
    option is only valid if it is a local user within Software Factory

There are a few optional arguments as well:

--insecure
    Disable SSL certificate verification. Enabled by default
--debug
    Enable debug messages in console. Disabled by default

Example usage
'''''''''''''

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password
           project create

Help
''''

Help is always available using the argument '-h':

.. code-block:: bash

 sfmanager project -h
 usage: sfmanager project [-h]
                          {delete_user,add_user,list_active_users,create,delete}
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

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           project create --name <project-name>

There are a few more options available in case you want to customize the
project.

--description [project-description], -d [project-description]
    An optional description of the project.

--upstream [GIT link], -u [GIT link]
    Uses the given repository to initalize the project, for example to reuse an existing Github repository

--upstream-ssh-key upstream-ssh-key
    SSH key for upstream repository if authentication is required

--core-group [core-group-members], -c [core-group-members]
    A list of comma-separated member ids that are setup as core reviewers. Core
    reviewers can approve or block patches; by default a review from at least
    one core is required to merge a patch.

--ptl-group [ptl-group-members], -p [ptl-group-members]
    A list of comma-separated member ids that are setup as PTLs (Project
    Technical Lead). The members can give core permissions to other users.

--dev-group [dev-group-members], -e [dev-group-members]
    A list of comma-separated member ids that are setup as developers of this
    project. Only required if a project is marked private.

--private
    Mark project as private. In that case only members of the dev, core or ptl
    group are allowed to access the project.

Delete Project
''''''''''''''

SF exposes ways to delete projects and the groups associated with the project in
Redmine and Gerrit simultaneously.

For any project, only the PTLs shall have the permission to delete it.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           project delete --name <project-name>


Group management
----------------

Default groups
''''''''''''''

When a project is created a few default project groups are created. To modify
these groups a user needs to be at least in the same group of users.

projectname-ptl
    Group of PTLs. Members can add other users to all groups.
projectname-core
    Group of core reviewers. Members can add other users to the groups
    projectname-core and projectname-dev
projectname-dev
    Group of developers, required when project is private. Members can not add
    any other user to any group.

Add user to project groups
''''''''''''''''''''''''''

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           project add_user --name user1 --groups p1-ptl,p1-core


List project users
''''''''''''''''''

Currently only lists all known users.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           project list_user


Remove user from project groups
'''''''''''''''''''''''''''''''

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           project delete_user --name user1 --group p1-ptl

If the request does not provide a specific group to delete the user from, SF
will remove the user from all groups associated to a project.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           project delete_user --name user1


User management
---------------

These commands manage the local users, that are not using external
authentication systems like Github.


Add user
''''''''

Creates a new local user and registers the user in Gerrit and Redmine

--username [username], -u [username]
    A unique username/login

--password [password], -p [password]
    The user password, can be provided interactively if this option is empty

--email [email], -e [email]
    The user email

--fullname [John Doe], -f [John Doe]
    The user's full name, defaults to username

--ssh-key [/path/to/pub_key], -s [/path/to/pub_key]
    The user's ssh public key file

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           user create --username jdoe --password secret --email jane@doe.org

Update user
'''''''''''

Update an existing local user. A user can update it's own details, and admins
can also update other user details. Takes the same arguments as user create.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           user update --username jdoe --password unguessable


Delete user
'''''''''''

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           user delete --username jdoe


Remote replication mangement
----------------------------

Add a new replication target
''''''''''''''''''''''''''''
Creating a new replication configuration requires several steps. These are:

replication_config add --section sectionname project projectname
    Creates a new configuration "sectionname" for the project "projectname"
replication_config add --section sectionname url gerrit@$hostname:/path/git/projectname.git
    Set the remote url to "gerrit@$hostname:/path/git/projectname.git"
trigger_replication --project config
    Trigger the replication

Example:

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           replication_config add --section sectionname project projectname

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           replication_config add --section sectionname url gerrit@$hostname:/path/git/projectname.git

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           trigger_replication --project config


List existing replication config
''''''''''''''''''''''''''''''''

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           replication_config list


Delete replication config
'''''''''''''''''''''''''

Deleting a replication target only stops replicating data to this target. It
does not remove data on the remote side.

.. code-block:: bash

 sfmanager --url <http://sfgateway.dom> \
           --auth-server-url <http://sfgateway.dom> \
           --auth user:password \
           remove-section sectionname


Backup and restore
------------------

Backups include data from Gerrit, Jenkins and Mysql. Because Mysql is used as
the default backend in Redmine, Paste and Etherpad all of this data is also
included in the backup file.

Create a new backup
'''''''''''''''''''

SF exposes ways to perform and retrieve a backup of all the user data store in
your SF installation. This backup can be used in case of disaster to quickly
recover user data on the same or another SF installation (of the same version).

Only the SF administrator can perform and retrieve a backup.

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
