
- The user object has a new fields: is_svn_user, svn_account and svn_passorwd. they can be modified on the users form by the admin user

- The admin user must be in the group Cotong Project Manager to be able to see the fields

- The user in Cotong project manager group can access the config menu in the project module.
	the "Module Transfer Settings" allows to set :
	- the absolute path of the SVN script used to transfer the module: e.g.: C:/Users/hp/Desktop/odoo_getaddon_script.sh
	- the absolute path of the addons directory: e.g: C:/Users/hp/Desktop/Test
	- the absolute path of the logs directory
	- the transfer stage; i.e: the stage in which when the task is dragged we need to get the last version of the module

-The project form has also new fields that only the Cotong Project manager can see:
* the svn repository path of the project: e.g: svn://repo.qitong.work/80serp
* a one2many fields to users that can drag the modules to transfer stage:
  those users can only be svn users(users whose the value of the field "is svn user" is true)

If a user, who is not a svn user assigned to the related project and the task, tries to drag the task in the upload stage, 
he will get an error

-the script is executed this way: 
script.sh <svn_repo> <svn_username> <svn_password> <addons_directory> <log_directory> <module_name>
or 
script.sh <svn_repo> <svn_username> <svn_password> <addons_directory> <log_directory> -r <revision_version> <module_name>

odoo uses the svn repo of the related project, the svn account and password of the current user, 
the name of task as name of the module(case sensitive, should contain no space), and the directories infos are read from 
the settings values.

- after the uplaod, the list of modules is updated and the module is installed if not yet, else it is upgraded.
It is not yet possible to handle the errors in the transfer process, 
but if the new module is now found on the server an exception is displayed; the stage of the task wont be upgraded



