#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import json
import re
# import requests
import time
import logging
import xml.etree.ElementTree as ET

#Modules maison
from mail import mail
from logs import logs
from Alma_Apis_Interface import Alma_Apis_Records
import Services

# Initilalisation des paramétres 
SERVICE ="delete_from_discovery"
INSTITUTION = 'UB'
INST_API_KEY = os.getenv('PROD_{}_BIB_API'.format(INSTITUTION))
NZ_API_KEY = os.getenv('PROD_NETWORK_BIB_API')
# INST_API_KEY = os.getenv('TEST_{}_API'.format(INSTITUTION))
# NZ_API_KEY = os.getenv('TEST_NETWORK_API')
SET_ID = '3391098080004672'

###Identifiants des jeux de résultats en fonction de l'institution
# UB = 3388855450004672

#On initialise le logger
logs.init_logs(os.getenv('LOGS_PATH'),SERVICE,'DEBUG')
log_module = logging.getLogger(SERVICE)

###MAIN####
inst_alma_api = Alma_Apis_Records.AlmaRecords(apikey=INST_API_KEY, region='EU', service=SERVICE)
nz_alma_api  = Alma_Apis_Records.AlmaRecords(apikey=NZ_API_KEY, region='EU', service=SERVICE)
log_module.info("DEBUT TRAITEMENT INSTITUTION\t{}".format(INSTITUTION))
# We'd created a set with records flaged as "Susppress from discovery"
inst_flaged_records_list = inst_alma_api.get_set_members_list(SET_ID)
# We loop into the list
for inst_flaged_record in inst_flaged_records_list :
    # we get the record from the institution to obtain the id of the record in the NZ 
    inst_record_id = inst_flaged_record[55:]
    log_module.debug(inst_record_id)
    status, xml_record = inst_alma_api.get_record(inst_record_id,view='full',expand='None',accept='xml')
    if status == 'Error'  :
        log_module.info("{}\t{}\tKO\t{}".format(inst_record_id,'Error',xml_record))
        continue
    inst_record = ET.fromstring(xml_record)
    # log_module.debug(xml_record)
    if inst_record.find(".//linked_record_id[@type='NZ']") is not None:
        bib_id = inst_record.find(".//linked_record_id[@type='NZ']").text
        bib_id_type = 'mms_id'
    elif inst_record.find(".//linked_record_id[@type='CZ']") is not None:
        bib_id = inst_record.find(".//linked_record_id[@type='CZ']").text
        bib_id_type = 'cz_mms_id'
    else :
        log_module.info("{}\t{}\tKO\t{}".format(inst_record_id,'Error',"Pas d'identifiant réseau - Notices locales"))
    log_module.debug("{} : {}".format(bib_id,bib_id_type))
    # we get the record from the NZ
    status, nz_xml_record = nz_alma_api.retrieve_record(bib_id_type,bib_id,view='full',expand='p_avail,e_avail,d_avail',accept='xml')
    if status == 'Error'  :
        log_module.info("{}\t{}\tKO\t{}".format(inst_record_id,bib_id,nz_xml_record))
        continue
    nz_result= ET.fromstring(nz_xml_record)
    nz_record= nz_result.find(".//bib")
    nz_id = nz_record.find(".//mms_id").text
    #we get the suppress from publishing flag
    suppress_flag = nz_record.find(".//suppress_from_publishing").text
    title = nz_record.find(".//title").text
    log_module.debug(suppress_flag)
    # if it's false we update it before
    if suppress_flag == 'true' :
        log_module.info("{}\t{}\tND\tNotice déjà supprimée de la découverte dans la NZ".format(inst_record_id,nz_id))
        continue
    log_module.debug(title)
    # We look if the record is present in other institutions
    ava_fields_list = nz_record.findall(".//record/datafield[@tag='AVE']")
    # Nodes for print inventory is taged 
    if not ava_fields_list :
        ava_fields_list = nz_record.findall(".//record/datafield[@tag='AVA']")
    # log_module.debug(ava_fields_list)
    can_suppress_record_in_nz = Services.get_other_institutions_suppress_flag(INSTITUTION,ava_fields_list,log_module)
    log_module.debug("#{}".format(can_suppress_record_in_nz))
    if can_suppress_record_in_nz :
        nz_record.find(".//suppress_from_publishing").text = 'true'
        status, response = nz_alma_api.update_record(nz_id,ET.tostring(nz_record))
        if status == "Success" :
            log_module.info("{}\t{}\tOK\tNotice tagué dans dans la NZ".format(inst_record_id,nz_id))
        else :
            log_module.info("{}\t{}\tKO\t{}".format(inst_record_id,nz_id,response))
    else : 
        log_module.info("{}\t{}\tND\tAu moins une institution est localisée sous la notice sans l'avoir masqué".format(inst_record_id,nz_id))
    log_module.debug("=======================================================================")        
log_module.info("FIN TRAITEMENT INSTITUTION\t{}".format(INSTITUTION))