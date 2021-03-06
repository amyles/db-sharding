#!/usr/bin/python

#############################
# Copyright 2020, Oracle Corporation and/or affiliates.  All rights reserved.
# Licensed under the Universal Permissive License v 1.0 as shown at http://oss.oracle.com/licenses/upl
# Author: paramdeep.saini@oracle.com
############################

import os
import os.path
import re
import socket
from oralogger import *
from oraenv import *
from oracommon import *
from oramachine import *

class OraGSM:
      """
      This calss setup the Gsm after DB installation.
      """
      def __init__(self,oralogger,orahandler,oraenv,oracommon):
        """
        This constructor of OraGsm class to setup the Gsm on primary DB.

        Attributes:
           oralogger (object): object of OraLogger Class.
           ohandler (object): object of Handler class.
           oenv (object): object of singleton OraEnv class.
           ocommon(object): object of OraCommon class.
           ora_env_dict(dict): Dict of env variable populated based on env variable for the setup.
           file_name(string): Filename from where logging message is populated.
        """
        self.ologger             = oralogger
        self.ohandler            = orahandler
        self.oenv                = oraenv.get_instance()
        self.ocommon             = oracommon
        self.ora_env_dict        = oraenv.get_env_vars()
        self.file_name           = os.path.basename(__file__)
        self.omachine            = OraMachine(self.ologger,self.ohandler,self.oenv,self.ocommon)

      def setup(self):
          """
           This function setup the Gsm on Primary DB.
          """
          self.setup_machine()
          self.gsm_checks()
          self.reset_gsm_setup()
          status = self.gsm_setup_check()
          if status:
             self.ocommon.log_info_message("Gsm Setup is already completed on this database",self.file_name)
             self.ocommon.start_gsm(self.ora_env_dict)
             self.ocommon.log_info_message("Started GSM",self.file_name)
          else:
             self.ocommon.log_info_message("No existing GDS found on this system. Setting up GDS on this machine.",self.file_name)
             self.setup_gsm_calog()
             self.setup_gsm_director()
             self.start_gsm_director()
             self.status_gsm_director()
             self.setup_gsm_shardg()
             self.setup_gsm_shard()
             self.set_hostid_null()
             self.stop_gsm_director()
             time.sleep(30)
             self.start_gsm_director()
             self.add_invited_node()
             self.remove_invited_node()
             self.stop_gsm_director()
             time.sleep(30)
             self.start_gsm_director()
             self.deploy_shard()
             self.setup_gsm_service()
             self.setup_sample_schema()
             self.gsm_backup_file()
             self.gsm_completion_message()
          ### Running Custom Scripts
          self.run_custom_scripts()   

      ###########  SETUP_MACHINE begins here ####################
      ## Function to machine setup
      def setup_machine(self):
          """
           This function performs the compute before performing setup
          """
          self.omachine.setup()

      ###########  SETUP_MACHINE ENDS here ####################

      def gsm_checks(self):
          """
          This function perform db checks before starting the setup
          """
          self.ohome_check()
          self.passwd_check()
          self.shard_user_check()
          self.gsm_hostname_check()
          self.director_params_checks()
	  self.catalog_params_check()
          self.shard_params_check()
          self.sgroup_params_check()

      def ohome_check(self):
                """
                   This function performs the oracle home related checks
                """
                if self.ocommon.check_key("ORACLE_HOME",self.ora_env_dict):
                   self.ocommon.log_info_message("ORACLE_HOME variable is set. Check Passed!",self.file_name)
                else:
                   self.ocommon.log_error_message("ORACLE_HOME variable is not set. Exiting!",self.file_name)
                   self.ocommon.prog_exit()

                if os.path.isdir(self.ora_env_dict["ORACLE_HOME"]):
                   msg='''ORACLE_HOME {0} dirctory exist. Directory Check passed!'''.format(self.ora_env_dict["ORACLE_HOME"])
                   self.ocommon.log_info_message(msg,self.file_name)
                else:
                   msg='''ORACLE_HOME {0} dirctory does not exist. Directory Check Failed!'''.format(self.ora_env_dict["ORACLE_HOME"])
                   self.ocommon.log_error_message(msg,self.file_name)
                   self.ocommon.prog_exit()

      def passwd_check(self):
                 """
                 This funnction perform password related checks
                 """
                 passwd_file_flag = False
                 if self.ocommon.check_key("SECRET_VOLUME",self.ora_env_dict) and check_key("COMMON_OS_PWD_FILE",self.ora_env_dict) and check_key("PWD_KEY",self.ora_env_dict):
                    msg='''SECRET_VOLUME passed as an env variable and set to {0}'''.format(self.ora_env_dict["SECRET_VOLUME"])
                 else:
                    self.ora_env_dict=self.ocommon.add_key("SECRET_VOLUME","/run/secrets",self.ora_env_dict)
                    msg='''SECRET_VOLUME not passed as an env variable. Setting default to {0}'''.format(self.ora_env_dict["SECRET_VOLUME"])

                 self.ocommon.log_warn_message(msg,self.file_name)

                 if self.ocommon.check_key("COMMON_OS_PWD_FILE",self.ora_env_dict):
                    msg='''COMMON_OS_PWD_FILE passed as an env variable and set to {0}'''.format(self.ora_env_dict["COMMON_OS_PWD_FILE"])
                 else:
                    self.ora_env_dict=self.ocommon.add_key("COMMON_OS_PWD_FILE","common_os_pwdfile.enc",self.ora_env_dict)
                    msg='''COMMON_OS_PWD_FILE not passed as an env variable. Setting default to {0}'''.format(self.ora_env_dict["COMMON_OS_PWD_FILE"])

                 self.ocommon.log_warn_message(msg,self.file_name)

                 if self.ocommon.check_key("PWD_KEY",self.ora_env_dict):
                    msg='''PWD_KEY passed as an env variable and set to {0}'''.format(self.ora_env_dict["PWD_KEY"])
                 else:
                    self.ora_env_dict=self.ocommon.add_key("PWD_KEY","pwd.key",self.ora_env_dict)
                    msg='''PWD_KEY not passed as an env variable. Setting default to {0}'''.format(self.ora_env_dict["PWD_KEY"])

                 self.ocommon.log_warn_message(msg,self.file_name)

                 secret_volume = self.ora_env_dict["SECRET_VOLUME"]
                 common_os_pwd_file = self.ora_env_dict["COMMON_OS_PWD_FILE"]
                 pwd_key = self.ora_env_dict["PWD_KEY"]
                 passwd_file='''{0}/{1}'''.format(self.ora_env_dict["SECRET_VOLUME"],self.ora_env_dict["COMMON_OS_PWD_FILE"])
                 if os.path.isfile(passwd_file):
                    msg='''Passwd file {0} exist. Password file Check passed!'''.format(passwd_file)
                    self.ocommon.log_info_message(msg,self.file_name)
                    msg='''Reading encrypted passwd from file {0}.'''.format(passwd_file)
                    self.ocommon.log_info_message(msg,self.file_name)
                    cmd='''openssl enc -d -aes-256-cbc -in \"{0}/{1}\" -out /tmp/{1} -pass file:\"{0}/{2}\"'''.format(secret_volume,common_os_pwd_file,pwd_key)
                    output,error,retcode=self.ocommon.execute_cmd(cmd,None,None)
                    self.ocommon.check_os_err(output,error,retcode,True)
                    passwd_file_flag = True

                 if not passwd_file_flag:
                #    cmd='''O$(openssl rand -base64 6 | tr -d "=+/")_1'''
                 #   output,error,retcode=self.ocommon.execute_cmd(cmd,None,None)
                    password="Oracle_19c"
                  #  self.ocommon.check_os_err('******',error,retcode,True)
                 else:
                    fname='''/tmp/{0}'''.format(common_os_pwd_file)
                    fdata=self.ocommon.read_file(fname)
                    password=fdata

                 if self.ocommon.check_key("ORACLE_PWD",self.ora_env_dict):
                    msg="ORACLE_PWD is passed as an env variable. Check Passed!"
                    self.ocommon.log_info_message(msg,self.file_name)
                 else:
                    self.ora_env_dict=self.ocommon.add_key("ORACLE_PWD",password,self.ora_env_dict)
                    msg="ORACLE_PWD set to HIDDEN_STRING generated using encrypted password file"
                    self.ocommon.log_info_message(msg,self.file_name)

      def shard_user_check(self):
                 """
                 This funnction set the user for pdb and cdb.
                 """
                 if self.ocommon.check_key("SHARD_ADMIN_USER",self.ora_env_dict):
                     msg='''SHARD_ADMIN_USER {0} is passed as an env variable. Check Passed!'''.format(self.ora_env_dict["SHARD_ADMIN_USER"])
                     self.ocommon.log_info_message(msg,self.file_name)
                 else:
                     self.ora_env_dict=self.ocommon.add_key("SHARD_ADMIN_USER","mysdbadmin",self.ora_env_dict)
                     msg="SHARD_ADMIN_USER is not set, setting default to mysdbadmin"
                     self.ocommon.log_info_message(msg,self.file_name)

                 if self.ocommon.check_key("PDB_ADMIN_USER",self.ora_env_dict):
                     msg='''PDB_ADMIN_USER {0} is passed as an env variable. Check Passed!'''.format(self.ora_env_dict["PDB_ADMIN_USER"])
                     self.ocommon.log_info_message(msg,self.file_name)
                 else:
                     self.ora_env_dict=self.ocommon.add_key("PDB_ADMIN_USER","PDBADMIN",self.ora_env_dict)
                     msg="PDB_ADMIN_USER is not set, setting default to PDBADMIN."
                     self.ocommon.log_info_message(msg,self.file_name)

      def director_params_checks(self):
                 """
                 This funnction check and set the shard director name
                 """
                 if self.ocommon.check_key("SHARD_DIRECTOR_PARAMS",self.ora_env_dict):
                     msg='''SHARD_DIRECTOR_PARAMS {0} is passed as an env variable. Check Passed!'''.format(self.ora_env_dict["SHARD_DIRECTOR_PARAMS"])
                     self.ocommon.log_info_message(msg,self.file_name)
                 else:
                     msg="SHARD_DIRECTOR_PARAMS is not set, Exiting the setup!"
                     self.ocommon.log_error_message(msg,self.file_name)
                     self.ocmmon.prog_exit("Exiting...")

      def gsm_hostname_check(self):
                 """
                 This function check and set the hostname.
                 """
                 if self.ocommon.check_key("ORACLE_HOSTNAME",self.ora_env_dict):
                    msg='''ORACLE_HOSTNAME {0} is passed as an env variable. Check Passed!'''.format(self.ora_env_dict["ORACLE_HOSTNAME"])
                    self.ocommon.log_info_message(msg,self.file_name)
                 else:
                    if self.ocommon.check_key("KUBE_SVC",self.ora_env_dict):
                       hostname='''{0}.{1}'''.format(socket.gethostname(),self.ora_env_dict["KUBE_SVC"])
                    else:
                       hostname='''{0}'''.format(socket.gethostname())
                    msg='''ORACLE_HOSTNAME is not set, setting it to hostname {0} of the compute!'''.format(hostname)
                    self.ora_env_dict=self.ocommon.add_key("ORACLE_HOSTNAME",hostname,self.ora_env_dict)
                    self.ocommon.log_info_message(msg,self.file_name)

      def catalog_params_check(self):
                 """
                 This funnction check if CATALOG[1-9]_PARAMS such as CATALOG_PARAMS is passed as an env variable or not. If not passed then exit.
                 """
                 status=False
                 reg_exp= self.catalog_regex() 
                 for key in self.ora_env_dict.keys():
                     if(reg_exp.match(key)):
                        msg='''CATALOG PARAMS {0} is set to {1}'''.format(key,self.ora_env_dict[key])
                        self.ocommon.log_info_message(msg,self.file_name)
                        status=True

                 if not status:
                     msg="CATALOG[1-9]_PARAMS such as CATALOG_PARAMS is not set, exiting!"
                     self.ocommon.log_error_message(msg,self.file_name)
                     self.ocommon.prog_exit("Exiting..")

      def shard_params_check(self):
                 """
                 This funnction check if SHARD[1-9]_PARAMS such as SHARD1_PARAMS is passed as an env variable or not. If not passed then exit.
                 """
                 status=False
                 reg_exp= self.shard_regex()
                 for key in self.ora_env_dict.keys():
                     if(reg_exp.match(key)):
                        msg='''SHARD PARAMS {0} is set to {1}'''.format(key,self.ora_env_dict[key])
                        self.ocommon.log_info_message(msg,self.file_name)
                        status=True

                 if not status:
                     msg="SHARD[1-9]_PARAMS such as SHARD1_PARAMS is not set, exiting!"
                     self.ocommon.log_error_message(msg,self.file_name)
                     self.ocommon.prog_exit()

      def sgroup_params_check(self):
                 """
                 This funnction check if SHARD[1-9]_GROUP_PARAMS such as SHARD1_GROUP_PARAMS is passed as an env variable or not. If not passed then exit.
                 """
                 status=False
                 reg_exp= self.shardg_regex()
                 for key in self.ora_env_dict.keys():
                     if(reg_exp.match(key)):
                        msg='''SHARD GROUP PARAMS {0} is set to {1}'''.format(key,self.ora_env_dict[key])
                        self.ocommon.log_info_message(msg,self.file_name)
                        status=True

                 if not status:
                     msg="SHARD[1-9]_GROUP_PARAMS such as SHARD1_PARAMS is not set, exiting!"
                     self.ocommon.log_error_message(msg,self.file_name)
                     self.ocommon.prog_exit()


             ###########  DB_CHECKS  Related Functions Begin Here  ####################


             ########## SETUP_CDB_catalog FUNCTION BEGIN HERE ###############################
      def reset_gsm_setup(self):
                 """
                  This function delete the GSM files.
                 """
                 self.ocommon.log_info_message("Inside reset_gsm_setup",self.file_name)
                 gsmdata_loc='/opt/oracle/gsmdata'
                 cmd_list=[]
                 if self.ocommon.check_key("RESET_ENV",self.ora_env_dict):
                    if self.ora_env_dict["RESET_ENV"]:
                       msg='''Deleteing files from {0}'''.format(gsmdata_loc)
                       self.ocommon.log_info_message(msg,self.file_name)
                       cmd_list[0]='''rm -f {0}/gsm.ora'''.format(gsmdata_loc)
                       cmd_list[1]='''rm -f {0}/tnsnames.ora'''.format(gsmdata_loc)
                       cmd_list[2]='''rm -rf {0}/wallets'''.format(gsmdata_loc)
                    for cmd in cmd_list:
                        output,error,retcode=self.ocommon.execute_cmd(cmd,None,None)
                        self.ocommon.check_os_err(output,error,retcode,True)

      def gsm_setup_check(self):
                 """
                  This function chck if GSM is already setup on this
                 """
                 status=True
                 self.ocommon.log_info_message("Inside reset_gsm_setup",self.file_name)
                 gsmdata_loc='/opt/oracle/gsmdata'
                 gsmfile_loc='''{0}/network/admin'''.format(self.ora_env_dict["ORACLE_HOME"])

                 gsmora='''{0}/gsm.ora'''.format(gsmdata_loc)
                 tnsnamesora='''{0}/tnsnames.ora'''.format(gsmdata_loc)
                 walletloc='''{0}/gsmwallet'''.format(gsmdata_loc)

                 if os.path.isfile(gsmora):
                    cmd='''cp -r -v -f {0} {1}/'''.format(gsmora,gsmfile_loc)
                    output,error,retcode=self.ocommon.execute_cmd(cmd,None,None)
                    self.ocommon.check_os_err(output,error,retcode,True)
                 else:
                    status=False

                 if os.path.isfile(tnsnamesora):
                    cmd='''cp -r -v -f {0} {1}/'''.format(tnsnamesora,gsmfile_loc)
                    output,error,retcode=self.ocommon.execute_cmd(cmd,None,None)
                    self.ocommon.check_os_err(output,error,retcode,True)
                 else:
                    status=False

                 if os.path.isdir(walletloc):
                    cmd='''cp -r -v -f {0} {1}/'''.format(walletloc,gsmfile_loc)
                    output,error,retcode=self.ocommon.execute_cmd(cmd,None,None)
                    self.ocommon.check_os_err(output,error,retcode,True)
                 else:
                    status=False

                 if status:
                    return True
                 else:
                    return False

      ####################  Catalog related Functions BEGINS Here ###########################
      def setup_gsm_calog(self):
                 """
                  This function setup the GSM catalog.
                 """
                 self.ocommon.log_info_message("Inside setup_gsm_calog()",self.file_name)
                 status=False
                 reg_exp= self.catalog_regex()
                 counter=1
                 end_counter=60
                 catalog_db_status=None
                 while counter < end_counter:                 
                       for key in self.ora_env_dict.keys():
                           if(reg_exp.match(key)):
                              catalog_db,catalog_pdb,catalog_port,catalog_region,catalog_host,catalog_name=self.process_clog_vars(key)
                              catalog_db_status=self.check_setup_status(catalog_host,catalog_db,catalog_pdb,catalog_port)
                              if catalog_db_status == 'completed':
                                 self.configure_gsm_clog(catalog_host,catalog_db,catalog_pdb,catalog_port,catalog_name,catalog_region)
                                 break 
                              else:
                                 msg='''Catalog Status must return completed but returned value is {0}'''.format(status)
                                 self.ocommon.log_info_message(msg,self.file_name)
                       if catalog_db_status == 'completed':
                          break
                       else:
                         msg='''Catalog setup is still not completed in GSM. Sleeping for 60 seconds and sleeping count is {0}'''.format(counter)
                         self.ocommon.log_info_message(msg,self.file_name)
                         time.sleep(60)
                         counter=counter+1

      def process_clog_vars(self,key):
          """
          This function process catalog vars based on key and return values to configure the GSM
          """
          catalog_db=None
          catalog_pdb=None
          catalog_port=None
          catalog_region=None
          catalog_host=None
          catalog_name=None

          self.ocommon.log_info_message("Inside process_clog_vars()",self.file_name)
          cvar_str=self.ora_env_dict[key]
          cvar_dict=dict(item.split("=") for item in cvar_str.split(";"))
          for ckey in cvar_dict.keys():
              if ckey == 'catalog_db':
                 catalog_db = cvar_dict[ckey]
              if ckey == 'catalog_pdb':
                 catalog_pdb = cvar_dict[ckey]
              if ckey == 'catalog_port':
                 catalog_port = cvar_dict[ckey]
              if ckey == 'catalog_region':
                 catalog_region = cvar_dict[ckey]
              if ckey == 'catalog_host':
                 catalog_host = cvar_dict[ckey]
              if ckey == 'catalog_name':
                 catalog_name = cvar_dict[ckey]
              ## Set the values if not set in above block
          if not catalog_port:
              catalog_port=1521
          if not catalog_region:
              catalog_region="region1,region2"

              ### Check values must be set
          if catalog_host and catalog_db and catalog_pdb and catalog_port and catalog_region and catalog_name:
              return catalog_db,catalog_pdb,catalog_port,catalog_region,catalog_host,catalog_name
          else:
              msg1='''catalog_db={0},catalog_pdb={1}'''.format((catalog_db or "Missing Value"),(catalog_pdb or "Missing Value"))
              msg2='''catalog_port={0},catalog_host={1}'''.format((catalog_port or "Missing Value"),(catalog_host or "Missing Value"))
              msg3='''catalog_region={0},catalog_name={1}'''.format((catalog_region or "Missing Value"),(catalog_name or "Missing Value"))
              msg='''Catalog params {0} is not set correctly. One or more value is missing {1} {2} {3}'''.format(key,msg1,msg2,msg3)
              self.ocommon.log_info_message(msg,self.file_name)
              self.ocommon.prog_exit("Error occurred")

      def check_gsm_catalog(self):
          """
           This function check the catalog status in GSM
          """
          self.ocommon.log_info_message("Inside check_gsm_catalog()",self.file_name)
          dtrname,dtrport,dtregion=self.process_director_vars()
          gsmcmd='''
            set gsm -gsm {0};
            status gsm;
            exit;
          '''.format(dtrname)
          output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)
          new_output=output[0].replace(" ","")
          self.ocommon.log_info_message(new_output,self.file_name)
          match=self.ocommon.check_substr_match(new_output,"ConnectedtoGDScatalogY")
          return(self.ocommon.check_status_value(match))

      def catalog_regex(self):
          """
            This function return the rgex to search the CATALOG PARAMS
          """ 
          self.ocommon.log_info_message("Inside catalog_regex()",self.file_name)
          return re.compile('CATALOG_PARAMS') 

      
      def configure_gsm_clog(self,chost,ccdb,cpdb,cport,catalog_name,catalog_region):
                 """
                  This function configure the GSM catalog.
                 """
                 self.ocommon.log_info_message("Inside configure_gsm_clog()",self.file_name)
                 gsmhost=self.ora_env_dict["ORACLE_HOSTNAME"]
                 cadmin=self.ora_env_dict["SHARD_ADMIN_USER"]
                 cpasswd="HIDDEN_STRING"
                 self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
                 gsmlogin='''{0}/bin/gdsctl'''.format(self.ora_env_dict["ORACLE_HOME"])
                 gsmcmd='''
                  create shardcatalog -database \"(DESCRIPTION=(ADDRESS=(PROTOCOL=tcp)(HOST={0})(PORT={1}))(CONNECT_DATA=(SERVICE_NAME={2})))\" -chunks 12 -user {3}/{4} -sdb {5} -region {6} -agent_port 8080 -agent_password {4} -autovncr off;
                  add invitednode {0};
                  exit;
                  '''.format(chost,cport,cpdb,cadmin,cpasswd,catalog_name,catalog_region)

                 output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)
                 ### Unsetting the encrypt value to None
                 self.ocommon.unset_mask_str()

      ########################################   GSM director Functions Begins Here #####################
      def process_director_vars(self):
          """
          This function process GSM director vars based on key and return values to configure the GSM
          """
          dtrname=None
          dtrport=None
          dtregion=None

          self.ocommon.log_info_message("Inside process_director_vars()",self.file_name)
          cvar_str=self.ora_env_dict["SHARD_DIRECTOR_PARAMS"]
          cvar_dict=dict(item.split("=") for item in cvar_str.split(";"))
          for ckey in cvar_dict.keys():
              if ckey == 'director_name':
                 dtrname = cvar_dict[ckey]
              if ckey == 'director_port':
                 dtrport = cvar_dict[ckey]
              if ckey == 'director_region':
                 dtregion = cvar_dict[ckey]

              ### Check values must be set
          if dtrname and dtrport and dtregion:
             return dtrname,dtrport,dtregion
          else:
             msg1='''director_name={0},director_port={1}'''.format((director_name or "Missing Value"),(director_port or "Missing Value"))
             msg2='''director_region={0}'''.format((director_region or "Missing Value"))
             msg='''Director params {0} is not set correctly. One or more value is missing {1} {2}'''.format(SHARD_DIRECTOR_PARAMS,msg1,msg2)
             self.ocommon.log_error_message(msg,self.file_name)
             self.ocommon.prog_exit("Error occurred")

      def check_gsm_director(self):
          """
          This function check the GSM director status
          """  
          self.ocommon.log_info_message("Inside check_gsm_director()",self.file_name)
          dtrname,dtrport,dtregion=self.process_director_vars()
          gsmcmd='''
            set gsm -gsm {0};
            config;
            exit;
          '''.format(dtrname)
          output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)
          matched_output=re.findall("(?:GSMs\n)(?:.+\n)+",output)
          match=self.ocommon.check_substr_match(matched_output[0],dtrname)
          return(self.ocommon.check_status_value(match))

      def setup_gsm_director(self):
                 """
                 This function add the shard in the GSM
                 """
                 self.ocommon.log_info_message("Inside setup_gsm_director()",self.file_name)
                 gsmhost=self.ora_env_dict["ORACLE_HOSTNAME"]
                 cadmin=self.ora_env_dict["SHARD_ADMIN_USER"]
                 cpasswd="HIDDEN_STRING"
                 dtrname,dtrport,dtregion=self.process_director_vars()
                 ## Getting the values of catalog_port,catalog_pdb,catalog_host
                 reg_exp= self.catalog_regex()
                 for key in self.ora_env_dict.keys():
                     if(reg_exp.match(key)):
                        catalog_db,catalog_pdb,catalog_port,catalog_region,catalog_host,catalog_name=self.process_clog_vars(key)
                 self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
                 gsmcmd='''
                  add gsm -gsm {0}  -listener {1} -pwd {2} -catalog {3}:{4}/{5}  -region {6} -endpoint '(ADDRESS=(PROTOCOL=tcp)(HOST={7})(PORT={1}))';
                  exit;
                  '''.format(dtrname,"1521",cpasswd,catalog_host,catalog_port,catalog_pdb,dtregion,gsmhost)
                 output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)

                 ### Unsetting the encrypt value to None
                 self.ocommon.unset_mask_str()
                
      def start_gsm_director(self):
                 """
                 This function start the director in the GSM
                 """
                 dtrname,dtrport,dtregion=self.process_director_vars()
                 gsmcmd='''
                   start gsm -gsm {0};
                  exit;
                  '''.format(dtrname)
                 output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)

      def stop_gsm_director(self):
                 """
                 This function stop the director in the GSM
                 """
                 dtrname,dtrport,dtregion=self.process_director_vars()
                 gsmlogin='''{0}/bin/gdsctl'''.format(self.ora_env_dict["ORACLE_HOME"])
                 gsmcmd='''
                   stop gsm -gsm {0};
                  exit;
                  '''.format(dtrname)
                 output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)

      def status_gsm_director(self):
                 """
                 This function stop the director in the GSM
                 """
                 gsm_status = self.check_gsm_director()
                 catalog_status = self.check_gsm_catalog()

                 if gsm_status == 'completed':
                    msg='''Director setup completed in GSM and catalog is connected'''
                    self.ocommon.log_info_message(msg,self.file_name)
                 else:
                    msg='''Shard director in GSM did not complete or not connected to catalog. Exiting...'''
                    self.ocommon.log_error_message(msg,self.file_name)
                    self.ocommon.prog_exit("127")

      ######################################## Shard Group Setup Begins Here ############################
      def setup_gsm_shardg(self):
                 """
                  This function setup the shard group.
                 """
                 self.ocommon.log_info_message("Inside setup_gsm_shardg()",self.file_name)
                 status=False
                 reg_exp= self.shardg_regex()
                 counter=1
                 end_counter=3
                 while counter < end_counter:
                       for key in self.ora_env_dict.keys():
                           if(reg_exp.match(key)):
                              shard_group_status=None
                              group_name,deploy_as,group_region=self.process_shardg_vars(key)
                              shard_group_status=self.check_shardg_status(group_name)
                              if shard_group_status != 'completed':
                                 self.configure_gsm_shardg(group_name,deploy_as,group_region)

                       status = self.check_shardg_status(None)
                       if status == 'completed':
                          break
                       else:
                         msg='''GSM shard group setup is still not completed in GSM. Sleeping for 60 seconds and sleeping count is {0}'''.format(counter)
                         time.sleep(60)
                         counter=counter+1

                 status = self.check_shardg_status(None)
                 if status == 'completed':
                    msg='''Shard group setup completed in GSM'''
                    self.ocommon.log_info_message(msg,self.file_name)
                 else:
                    msg='''Waited 2 minute to complete catalog setup in GSM but setup did not complete or failed. Exiting...'''
                    self.ocommon.log_error_message(msg,self.file_name)
                    self.ocommon.prog_exit("127")

      def process_shardg_vars(self,key):
          """
          This function process shardG vars based on key and return values to configure the GSM
          """
          group_name=None
          deploy_as=None
          group_region=None
 
          self.ocommon.log_info_message("Inside process_shardg_vars()",self.file_name)
          cvar_str=self.ora_env_dict[key]
          cvar_dict=dict(item.split("=") for item in cvar_str.split(";"))
          for ckey in cvar_dict.keys():
              if ckey == 'group_name':
                 group_name = cvar_dict[ckey]
              if ckey == 'deploy_as':
                 deploy_as = cvar_dict[ckey]
              if ckey == 'group_region':
                 group_region = cvar_dict[ckey]

              ### Check values must be set
          if group_name and deploy_as and group_region:
             return group_name,deploy_as,group_region
          else:
             msg1='''group_name={0},deploy_as={1}'''.format((group_name or "Missing Value"),(deploy_as or "Missing Value"))
             msg2='''group_region={0}'''.format((group_region or "Missing Value"))
             msg='''Shard group params {0} is not set correctly. One or more value is missing {1} {2}'''.format(key,msg1,msg2)
             self.ocommon.log_error_message(msg,self.file_name)
             self.ocommon.prog_exit("Error occurred")

      def check_shardg_status(self,group_name):
          """
           This function check the shard status in GSM
          """
          self.ocommon.log_info_message("Inside check_shardg_status()",self.file_name)
          dtrname,dtrport,dtregion=self.process_director_vars()
          gsmcmd='''
            set gsm -gsm {0};
            config;
            exit;
          '''.format(dtrname)
          output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)
          matched_output=re.findall("(?:Shard Groups\n)(?:.+\n)+",output)
          status=False
          if group_name:
             if self.ocommon.check_substr_match(matched_output[0],group_name):
                status=True
             else:
                status=False
          else:   
             reg_exp= self.shardg_regex()
             for key in self.ora_env_dict.keys():
                 if(reg_exp.match(key)):
                     group_name,deploy_as,group_region=self.process_shardg_vars(key)
                   #  match=re.search("(?i)(?m)"+group_name,matched_output)
                     if self.ocommon.check_substr_match(matched_output[0],group_name):
                          status=True
                     else:
                          status=False
          return(self.ocommon.check_status_value(status))

      def shardg_regex(self):
          """
            This function return the rgex to search the SHARD GROUP PARAMS
          """
          self.ocommon.log_info_message("Inside shardg_regex()",self.file_name)
          return re.compile('SHARD[0-9]+_GROUP_PARAMS')

      def configure_gsm_shardg(self,group_name,deploy_as,group_region):
                 """
                  This function configure the Shard Group.
                 """
                 self.ocommon.log_info_message("Inside configure_gsm_shardg()",self.file_name)
                 gsmhost=self.ora_env_dict["ORACLE_HOSTNAME"]
                 cadmin=self.ora_env_dict["SHARD_ADMIN_USER"]
                 cpasswd="HIDDEN_STRING"

                 dtrname,dtrport,dtregion=self.process_director_vars()
                 self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
                 gsmlogin='''{0}/bin/gdsctl'''.format(self.ora_env_dict["ORACLE_HOME"])
                 gsmcmd='''
                   set gsm -gsm {0};
                   connect {1}/{2};
                   add shardgroup -shardgroup {3} -deploy_as {4} -region {5}
                 exit;
                  '''.format(dtrname,cadmin,cpasswd,group_name,deploy_as,group_region)
                 output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)                 

                 ### Unsetting the encrypt value to None
                 self.ocommon.unset_mask_str()

        #########################################Shard Function Begins Here ##############################
      def setup_gsm_shard(self):
                """
                This function add the shard in the GSM
                """
                self.ocommon.log_info_message("Inside setup_gsm_shard()",self.file_name)
                status=False
                reg_exp= self.shard_regex()
                counter=1
                end_counter=60
                while counter < end_counter:                 
                      for key in self.ora_env_dict.keys():
                          if(reg_exp.match(key)):
                             shard_db_status=None
                             shard_db,shard_pdb,shard_port,shard_group,shard_host=self.process_shard_vars(key)

                             shard_db_status=self.check_setup_status(shard_host,shard_db,shard_pdb,shard_port)
                             if shard_db_status == 'completed':
                                self.configure_gsm_shard(shard_host,shard_db,shard_pdb,shard_port,shard_group)
                             else:
                                msg='''Shard db status must return completed but returned value is {0}'''.format(status)
                                self.ocommon.log_info_message(msg,self.file_name)
                                
                      status = self.check_shard_status(None) 
                      if status == 'completed':
                         break
                      else:
                         msg='''Shard DB setup is still not completed in GSM. Sleeping for 60 seconds and sleeping count is {0}'''.format(counter)
                         self.ocommon.log_info_message(msg,self.file_name)
                         time.sleep(60)
                         counter=counter+1

                status = self.check_shard_status(None)
                if status == 'completed':
                   msg='''Shard DB setup completed in GSM'''
                   self.ocommon.log_info_message(msg,self.file_name)
                else:
                   msg='''Waited 60 minute to complete shard db setup in GSM but setup did not complete or failed. Exiting...'''
                   self.ocommon.log_error_message(msg,self.file_name)
                   self.ocommon.prog_exit("127")     

      def process_shard_vars(self,key):
          """
          This function process sgard vars based on key and return values to configure the GSM
          """
          shard_db=None
          shard_pdb=None
          shard_port=None
          shard_group=None
          shard_host=None

          self.ocommon.log_info_message("Inside process_shard_vars()",self.file_name)
          cvar_str=self.ora_env_dict[key]
          cvar_dict=dict(item.split("=") for item in cvar_str.split(";"))
          for ckey in cvar_dict.keys():
              if ckey == 'shard_db':
                 shard_db = cvar_dict[ckey]
              if ckey == 'shard_pdb':
                 shard_pdb = cvar_dict[ckey]
              if ckey == 'shard_port':
                 shard_port = cvar_dict[ckey]
              if ckey == 'shard_group':
                 shard_group = cvar_dict[ckey]
              if ckey == 'shard_host':
                 shard_host = cvar_dict[ckey]
              ## Set the values if not set in above block
          if not shard_port:
             shard_port=1521

              ### Check values must be set
          if shard_host and shard_db and shard_pdb and shard_port and shard_group:
              return shard_db,shard_pdb,shard_port,shard_group,shard_host
          else:
              msg1='''shard_db={0},shard_pdb={1}'''.format((shard_db or "Missing Value"),(shard_pdb or "Missing Value"))
              msg2='''shard_port={0},shard_host={1}'''.format((shard_port or "Missing Value"),(shard_host or "Missing Value"))
              msg3='''shard_group={1}'''.format((shard_group or "Missing Value"))
              msg='''Shard DB  params {0} is not set correctly. One or more value is missing {1} {2} {3}'''.format(key,msg1,msg2,msg3)
              self.ocommon.log_info_message(msg,self.file_name)
              self.ocommon.prog_exit("Error occurred")

      def check_shard_status(self,shard_name):
          """
           This function check the shard status in GSM
          """
          self.ocommon.log_info_message("Inside check_shard_status()",self.file_name)
          dtrname,dtrport,dtregion=self.process_director_vars()
          gsmcmd='''
            set gsm -gsm {0};
            config;
            exit;
          '''.format(dtrname)
          output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)
          matched_output=re.findall("(?:Databases\n)(?:.+\n)+",output)
          status=False
          if shard_name:
             if self.ocommon.check_substr_match(matched_output[0],shard_name.lower()):
                status=True
             else:
                status=False
          else:
             reg_exp= self.shard_regex()
             for key in self.ora_env_dict.keys():
                 if(reg_exp.match(key)):
                   shard_db,shard_pdb,shard_port,shard_region,shard_host=self.process_shard_vars(key)
                   shard_name='''{0}_{1}'''.format(shard_db,shard_pdb)
                   if self.ocommon.check_substr_match(matched_output[0],shard_name.lower()):
                      status=True
                   else:
                      status=False
          return(self.ocommon.check_status_value(status))

      def shard_regex(self):
          """
            This function return the rgex to search the SHARD PARAMS
          """ 
          self.ocommon.log_info_message("Inside shard_regex()",self.file_name)
          return re.compile('SHARD[0-9]+_PARAMS') 

      def configure_gsm_shard(self,shost,scdb,spdb,sdbport,sgroup):
                 """
                  This function configure the shard db.
                 """
                 spasswd="HIDDEN_STRING"
                 admuser= self.ora_env_dict["SHARD_ADMIN_USER"]
                 dtrname,dtrport,dtregion=self.process_director_vars()
                 self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
                 gsmcmd='''
                  set gsm -gsm {0};
                  connect {1}/{2};
                  add cdb -connect {3}:{4}:{5} -pwd {2};
                  add shard -cdb {5} -connect {3}:{4}/{6} -shardgroup {7} -pwd {2};
                  config vncr;
                  exit;
                  '''.format(dtrname,admuser,spasswd,shost,sdbport,scdb,spdb,sgroup)

                 output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)
                 ### Unsetting the encrypt value to None
                 self.ocommon.unset_mask_str()

      def set_hostid_null(self):
          """
           This function set the hostid to Null
          """
          spasswd="HIDDEN_STRING"
          admuser= self.ora_env_dict["SHARD_ADMIN_USER"]
          reg_exp= self.catalog_regex()
          for key in self.ora_env_dict.keys():
              if(reg_exp.match(key)):
                 catalog_db,catalog_pdb,catalog_port,catalog_region,catalog_host,catalog_name=self.process_clog_vars(key)
                 sqlpluslogin='''{0}/bin/sqlplus "sys/HIDDEN_STRING@{1}:{2}/{3} as sysdba"'''.format(self.ora_env_dict["ORACLE_HOME"],catalog_host,catalog_port,catalog_pdb,admuser)
                 self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
                 msg='''Setting host Id null in catalog as auto vncr is disabled'''
                 self.ocommon.log_info_message(msg,self.file_name)
                 sqlcmd='''
                  set echo on
                  set termout on
                  set time on
                  update gsmadmin_internal.database set hostid=NULL;
                 '''
                 output,error,retcode=self.ocommon.run_sqlplus(sqlpluslogin,sqlcmd,None)
                 self.ocommon.log_info_message("Calling check_sql_err() to validate the sql command return status",self.file_name)
                 self.ocommon.check_sql_err(output,error,retcode,None)
                 self.ocommon.unset_mask_str()

      def add_invited_node(self):
                """
                This function add the invited in the GSM configuration
                """
                self.ocommon.log_info_message("Inside add_invited_node()",self.file_name)
                reg_exp= self.shard_regex()
                gsmhost=self.ora_env_dict["ORACLE_HOSTNAME"]
                cadmin=self.ora_env_dict["SHARD_ADMIN_USER"]
                cpasswd="HIDDEN_STRING"
                dtrname,dtrport,dtregion=self.process_director_vars()
                self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
                for key in self.ora_env_dict.keys():
                    if(reg_exp.match(key)):
                        shard_db,shard_pdb,shard_port,shard_region,shard_host=self.process_shard_vars(key)
                        gsmcmd='''
                         set gsm -gsm {0};
                         connect {1}/{2};
                         add invitednode {3};
                         exit;
                        '''.format(dtrname,cadmin,cpasswd,shard_host)
                        output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)

      def remove_invited_node(self):
                """
                This function remove the invited in the GSM configuration
                """
                self.ocommon.log_info_message("Inside remove_invited_node()",self.file_name)
                reg_exp= self.shard_regex()
                gsmhost=self.ora_env_dict["ORACLE_HOSTNAME"]
                cadmin=self.ora_env_dict["SHARD_ADMIN_USER"]
                cpasswd="HIDDEN_STRING"
                dtrname,dtrport,dtregion=self.process_director_vars()
                self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])

                if self.ocommon.check_key("KUBE_SVC",self.ora_env_dict):
                   for key in self.ora_env_dict.keys():
                       if(reg_exp.match(key)):
                           shard_db,shard_pdb,shard_port,shard_region,shard_host=self.process_shard_vars(key)
                           temp_host= shard_host.split('.',1)[0] 
                           gsmcmd='''
                            set gsm -gsm {0};
                            connect {1}/{2};
                            remove invitednode {3};
                            exit;
                           '''.format(dtrname,cadmin,cpasswd,temp_host)
                           output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)
                else:
                   self.ocommon.log_info_message("KUBE_SVC is not set. No need to remove invited node!",self.file_name)  


      def deploy_shard(self):
                """
                This function deploy shard
                """
                self.ocommon.log_info_message("Inside deploy_shard()",self.file_name)
                gsmhost=self.ora_env_dict["ORACLE_HOSTNAME"]
                cadmin=self.ora_env_dict["SHARD_ADMIN_USER"]
                cpasswd="HIDDEN_STRING"
                gsmlogin='''{0}/bin/gdsctl'''.format(self.ora_env_dict["ORACLE_HOME"])
                dtrname,dtrport,dtregion=self.process_director_vars()
                self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
                gsmcmd='''
                 set gsm -gsm {0};
                 connect {1}/{2};
                 config shardspace;
                 config shardgroup;
                 config vncr;
                 deploy;
                 config shard; 
                 exit;
                 '''.format(dtrname,cadmin,cpasswd)
                output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)
                 ### Unsetting the encrypt value to None
                self.ocommon.unset_mask_str()

      def check_setup_status(self,host,ccdb,svc,port):
            """
             This function check the shard status.
            """
            systemStr='''{0}/bin/sqlplus "system/HIDDEN_STRING@{1}:{2}/{3}"'''.format(self.ora_env_dict["ORACLE_HOME"],host,port,ccdb)
            
            fname='''/tmp/{0}'''.format("shard_setup.txt") 
            self.ocommon.remove_file(fname)
            self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
            msg='''Checking shardsetup table in CDB'''
            self.ocommon.log_info_message(msg,self.file_name)
            sqlcmd='''
            set heading off
            set feedback off
            set  term off
            SET NEWPAGE NONE
            spool {0}
            select * from shardsetup WHERE ROWNUM = 1;
            spool off
            exit;
            '''.format(fname)
            output,error,retcode=self.ocommon.run_sqlplus(systemStr,sqlcmd,None)
            self.ocommon.log_info_message("Calling check_sql_err() to validate the sql command return status",self.file_name)
            self.ocommon.check_sql_err(output,error,retcode,None)

            if os.path.isfile(fname): 
              fdata=self.ocommon.read_file(fname)
            else:
              fdata='nosetup'

           ### Unsetting the encrypt value to None
            self.ocommon.unset_mask_str()

            if re.search('completed',fdata):
              return 'completed'
            else:
              return 'notcompleted'

      ############################# Setup GSM Service ###############################################
      def setup_gsm_service(self):
                 """
                  This function setup the shard service.
                 """
                 self.ocommon.log_info_message("Inside setup_gsm_service()",self.file_name)
                 status=False
                 service_value="service_name=oltp_rw_svc;service_role=primary"
            #     self.ora_env_dict=self.ocommon.add_key("SERVICE1_PARAMS",service_value,self.ora_env_dict)
                 reg_exp= self.service_regex()
                 counter=1
                 end_counter=3
                 while counter < end_counter:
                       for key in self.ora_env_dict.keys():
                           if(reg_exp.match(key)):
                              shard_service_status=None
                              service_name,service_role=self.process_service_vars(key)
                              shard_service_status=self.check_service_status(service_name)
                              if shard_service_status != 'completed':
                                 self.configure_gsm_service(service_name,service_role)
                       status = self.check_service_status(None)
                       if status == 'completed':
                          break
                       else:
                         msg='''GSM service setup is still not completed in GSM. Sleeping for 60 seconds and sleeping count is {0}'''.format(counter)
                         time.sleep(60)
                         counter=counter+1

                 status = self.check_service_status(None)
                 if status == 'completed':
                    msg='''Shard service setup completed in GSM'''
                    self.ocommon.log_info_message(msg,self.file_name)
                 else:
                    msg='''Waited 2 minute to complete catalog setup in GSM but setup did not complete or failed. Exiting...'''
                    self.ocommon.log_error_message(msg,self.file_name)
                    self.ocommon.prog_exit("127")

      def process_service_vars(self,key):
          """
          This function process shardG vars based on key and return values to configure the GSM
          """
          service_name=None
          service_role=None

          self.ocommon.log_info_message("Inside process_service_vars()",self.file_name)
          cvar_str=self.ora_env_dict[key]
          cvar_dict=dict(item.split("=") for item in cvar_str.split(";"))
          for ckey in cvar_dict.keys():
              if ckey == 'service_name':
                 service_name = cvar_dict[ckey]
              if ckey == 'service_role':
                 service_role = cvar_dict[ckey]

              ### Check values must be set
          if service_name and service_role:
             return service_name,service_role
          else:
             msg1='''service_name={0},service_role={1}'''.format((service_name or "Missing Value"),(service_role or "Missing Value"))
             msg='''Shard service params {0} is not set correctly. One or more value is missing {1} {2}'''.format(key,msg1)
             self.ocommon.log_error_message(msg,self.file_name)
             self.ocommon.prog_exit("Error occurred")

      def check_service_status(self,service_name):
          """
           This function check the shard status in GSM
          """
          self.ocommon.log_info_message("Inside check_service_status()",self.file_name)
          dtrname,dtrport,dtregion=self.process_director_vars()
          gsmcmd='''
            set gsm -gsm {0};
            config;
            exit;
          '''.format(dtrname)
          output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)
          matched_output=re.findall("(?:Services\n)(?:.+\n)+",output)
          status=False
          if service_name:
             if self.ocommon.check_substr_match(matched_output[0],service_name):
                status=True
             else:
                status=False
          else:
             reg_exp= self.service_regex()
             for key in self.ora_env_dict.keys():
                 if(reg_exp.match(key)):
                     service_name,service_role=self.process_service_vars(key)
                   #  match=re.search("(?i)(?m)"+service_name,matched_output)
                     if self.ocommon.check_substr_match(matched_output[0],service_name):
                         status=True
                     else:
                         status=False

          return(self.ocommon.check_status_value(status))

      def service_regex(self):
          """
            This function return the rgex to search the SERVICE[0-9]_PARAMS
          """
          self.ocommon.log_info_message("Inside service_regex()",self.file_name)
          return re.compile('SERVICE[0-9]+_PARAMS')
		  
      def configure_gsm_service(self,service_name,service_role):
                 """
                  This function configure the service creation.
                 """
                 self.ocommon.log_info_message("Inside configure_gsm_service()",self.file_name)
                 gsmhost=self.ora_env_dict["ORACLE_HOSTNAME"]
                 cadmin=self.ora_env_dict["SHARD_ADMIN_USER"]
                 cpasswd="HIDDEN_STRING"

                 dtrname,dtrport,dtregion=self.process_director_vars()
                 self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
                 gsmlogin='''{0}/bin/gdsctl'''.format(self.ora_env_dict["ORACLE_HOME"])
                 gsmcmd='''
                   set gsm -gsm {0};
                   connect {1}/{2};
                   add service -service {3} -role {4};
                 exit;
                  '''.format(dtrname,cadmin,cpasswd,service_name,service_role)
                 output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)

                 ### Unsetting the encrypt value to None
                 self.ocommon.unset_mask_str()

      ############################## GSM backup fIle function Begins Here #############################
      def gsm_backup_file(self):
          """
            This function check the gsm setup status
          """
          self.ocommon.log_info_message("Inside gsm_backup_file()",self.file_name)
          gsmdata_loc='/opt/oracle/gsmdata'
          gsmfile_loc='''{0}/network/admin'''.format(self.ora_env_dict["ORACLE_HOME"])

          if os.path.isdir(gsmdata_loc):
             msg='''Directory {0} exit'''.format(gsmdata_loc)
             self.ocommon.log_info_message(msg,self.file_name)

          cmd='''cp -r -v {0}/* {1}/'''.format(gsmfile_loc,gsmdata_loc)
          output,error,retcode=self.ocommon.execute_cmd(cmd,None,None)
          self.ocommon.check_os_err(output,error,retcode,True)

      ############### Deploy Sample Function Begins Here ##########################
      def setup_sample_schema(self):
          """
            This function deploy the sample app
          """
          self.ocommon.log_info_message("Inside deploy_sample_schema()",self.file_name)
          reg_exp= self.catalog_regex()
          for key in self.ora_env_dict.keys():
              if(reg_exp.match(key)):
                 catalog_db,catalog_pdb,catalog_port,catalog_region,catalog_host,catalog_name=self.process_clog_vars(key)
          sqlpluslogin='''{0}/bin/sqlplus "sys/HIDDEN_STRING@{1}:{2}/{3} as sysdba"'''.format(self.ora_env_dict["ORACLE_HOME"],catalog_host,catalog_port,catalog_db)
          if self.ocommon.check_key("SAMPLE_SCHEMA",self.ora_env_dict):
             if self.ora_env_dict["SAMPLE_SCHEMA"] == 'DEPLOY':
                self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
                msg='''Deploying sample schema'''
                self.ocommon.log_info_message(msg,self.file_name)
                sqlcmd='''
                 set echo on
                 set termout on
                 set time on
                 spool /tmp/create_app_schema.lst
                 REM
                 REM Connect to the Shard Catalog and Create Schema
                 REM
                 alter session enable shard ddl;
                 alter session set container={2};
                 alter session enable shard ddl;
                 create user app_schema identified by app_schema;
                 grant connect, resource, alter session to app_schema;
                 grant execute on dbms_crypto to app_schema;
                 grant create table, create procedure, create tablespace, create materialized view to app_schema;
                 grant unlimited tablespace to app_schema;
                 grant select_catalog_role to app_schema;
                 grant all privileges to app_schema; 
                 grant gsmadmin_role to app_schema;
                 grant dba to app_schema;
                 CREATE TABLESPACE SET tbsset1 IN SHARDSPACE shd1;
                 CREATE TABLESPACE SET tbsset2 IN SHARDSPACE shd2;
                 connect app_schema/app_schema@{0}:{1}/{2}
                 alter session enable shard ddl;

                 /* Customer shard table */

                 CREATE SHARDED TABLE customer
                 ( cust_id NUMBER NOT NULL,
                  cust_passwd VARCHAR2(20) NOT NULL,
                  cust_name VARCHAR2(60) NOT NULL,
                  cust_type VARCHAR2(10) NOT NULL,
                  cust_email VARCHAR2(100) NOT NULL)
                  partitionset by list (cust_type)
                  partition by consistent hash (cust_id) partitions auto
                  (partitionset individual values ('individual') tablespace set tbsset1,
                  partitionset  business values ('business') tablespace set tbsset2
                  );
                 /* Invoice shard table */

                 CREATE SHARDED TABLE invoice 
                 ( invoice_id  NUMBER NOT NULL,
                 cust_id  NUMBER NOT NULL,
                 cust_type VARCHAR2(10) NOT NULL,
                 vendor_name VARCHAR2(60) NOT NULL,
                 balance FLOAT(10) NOT NULL,
                 total FLOAT(10) NOT NULL,    
                 status VARCHAR2(20),  
                 CONSTRAINT InvoicePK PRIMARY KEY (cust_id, invoice_id))
                 PARENT customer
                 partitionset by list (cust_type)
                 partition by consistent hash (cust_id) partitions auto
                 (partitionset individual values ('individual') tablespace set tbsset1,
                 partitionset  business values ('business') tablespace set tbsset2
                 );
                 /* Data */
                 insert into customer values (999, 'pass', 'Customer 999', 'individual', 'customer999@gmail.com');
                 insert into customer values (250251, 'pass', 'Customer 250251', 'individual', 'customer250251@yahoo.com');
                 insert into customer values (350351, 'pass', 'Customer 350351', 'individual', 'customer350351@gmail.com');
                 insert into customer values (550551, 'pass', 'Customer 550551', 'business', 'customer550551@hotmail.com');
                 insert into customer values (650651, 'pass', 'Customer 650651', 'business', 'customer650651@live.com');
                 insert into invoice values (1001, 999, 'individual', 'VendorA', 10000, 20000, 'Due');
                 insert into invoice values (1002, 999, 'individual', 'VendorB', 10000, 20000, 'Due');
                 insert into invoice values (1001, 250251, 'individual', 'VendorA', 10000, 20000, 'Due');
                 insert into invoice values (1002, 250251, 'individual', 'VendorB', 0, 10000, 'Paid');
                 insert into invoice values (1003, 250251, 'individual', 'VendorC', 14000, 15000, 'Due');
                 insert into invoice values (1001, 350351, 'individual', 'VendorD', 10000, 20000, 'Due');
                 insert into invoice values (1002, 350351, 'individual', 'VendorE', 0, 10000, 'Paid');
                 insert into invoice values (1003, 350351, 'individual', 'VendorF', 14000, 15000, 'Due');
                 insert into invoice values (1004, 350351, 'individual', 'VendorG', 12000, 15000, 'Due');
                 insert into invoice values (1001, 550551, 'business', 'VendorH', 10000, 20000, 'Due');
                 insert into invoice values (1002, 550551, 'business', 'VendorI', 0, 10000, 'Paid');
                 insert into invoice values (1003, 550551, 'business', 'VendorJ', 14000, 15000, 'Due');
                 insert into invoice values (1004, 550551, 'business', 'VendorK', 10000, 20000, 'Due');
                 insert into invoice values (1005, 550551, 'business', 'VendorL', 10000, 20000, 'Due');
                 insert into invoice values (1006, 550551, 'business', 'VendorM', 0, 10000, 'Paid');
                 insert into invoice values (1007, 550551, 'business', 'VendorN', 14000, 15000, 'Due');
                 insert into invoice values (1008, 550551, 'business', 'VendorO', 10000, 20000, 'Due');
                 insert into invoice values (1001, 650651, 'business', 'VendorT', 10000, 20000, 'Due');
                 insert into invoice values (1002, 650651, 'business', 'VendorU', 0, 10000, 'Paid');
                 insert into invoice values (1003, 650651, 'business', 'VendorV', 14000, 15000, 'Due');
                 insert into invoice values (1004, 650651, 'business', 'VendorW', 10000, 20000, 'Due');
                 insert into invoice values (1005, 650651, 'business', 'VendorX', 0, 20000, 'Paid');
                 insert into invoice values (1006, 650651, 'business', 'VendorY', 0, 30000, 'Paid');
                 insert into invoice values (1007, 650651, 'business', 'VendorZ', 0, 10000, 'Paid');
                 commit;
                 select table_name from user_tables;
                 spool off
                '''.format(catalog_host,catalog_port,catalog_pdb)
                output,error,retcode=self.ocommon.run_sqlplus(sqlpluslogin,sqlcmd,None)
                self.ocommon.log_info_message("Calling check_sql_err() to validate the sql command return status",self.file_name)
                self.ocommon.check_sql_err(output,error,retcode,None)
          ### Unsetting the encrypt value to None
                self.ocommon.unset_mask_str()

                gsmhost=self.ora_env_dict["ORACLE_HOSTNAME"]
                cadmin=self.ora_env_dict["SHARD_ADMIN_USER"]
                cpasswd="HIDDEN_STRING"
                dtrname,dtrport,dtregion=self.process_director_vars()
                self.ocommon.set_mask_str(self.ora_env_dict["ORACLE_PWD"])
                gsmcmd='''
                  set gsm -gsm {0};
                  connect {1}/{2};
                  show ddl;
                  exit;
                '''.format(dtrname,cadmin,cpasswd)
                output,error,retcode=self.ocommon.exec_gsm_cmd(gsmcmd,None,self.ora_env_dict)
          ### Unsetting the encrypt value to None
                self.ocommon.unset_mask_str()

          ###################################### Run custom scripts ##################################################
      def run_custom_scripts(self):
          """
           Custom script to be excuted on every restart of enviornment
          """
          self.ocommon.log_info_message("Inside run_custom_scripts()",self.file_name)
          if self.ocommon.check_key("CUSTOM_SHARD_SCRIPT_DIR",self.ora_env_dict): 
             shard_dir=self.ora_env_dict["CUSTOM_SHARD_SCRIPT_DIR"] 
             if self.ocommon.check_key("CUSTOM_SHARD_SCRIPT_FILE",self.ora_env_dict):
                shard_file=self.ora_env_dict["CUSTOM_SHARD_SCRIPT_FILE"]
                script_file = '''{0}/{1}'''.format(shard_dir,shard_file)  
                if os.path.isfile(script_file):
                   msg='''Custom shard script exist {0}'''.format(script_file) 
                   self.ocommon.log_info_message(msg,self.file_name) 
                   cmd='''sh {0}'''.format(script_file)
                   output,error,retcode=self.ocommon.execute_cmd(cmd,None,None)
                   self.ocommon.check_os_err(output,error,retcode,True)

      ############################### GSM Completion Message #######################################################
      def gsm_completion_message(self):
          """
           Funtion print completion message 
          """
          self.ocommon.log_info_message("Inside gsm_completion_message()",self.file_name)
          msg=[]
          msg.append('==============================================')
          msg.append('     GSM Setup Completed                      ')
          msg.append('==============================================')

          for text in msg:
              self.ocommon.log_info_message(text,self.file_name)
