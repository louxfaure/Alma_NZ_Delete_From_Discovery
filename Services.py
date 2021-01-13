#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import logging
import xml.etree.ElementTree as ET
from logs import logs
from Alma_Apis_Interface import Alma_Apis_Records

def get_record_supress_flag(institution,mms_id,log_module):
    """Use alma bib api tio get record in institution and return suppress from publishing flag

    Args:
        institution (string): [description]
        mms_id (string): [description]
        log_module (string): [description]
    """
    log_module.debug(mms_id)
    inst_alma_api = Alma_Apis_Records.AlmaRecords(apikey=os.getenv('PROD_{}_BIB_API'.format(institution)), region='EU', service="delete_from_discovery")
    status, xml_record = inst_alma_api.get_record(mms_id,view='full',expand='None',accept='xml')
    if status == 'Error':
        log_module.info(log_module.info("{}\tND\tKO\t{}\t{}".format(inst_record_id,response,institution)))
        return status
    inst_record = ET.fromstring(xml_record)
    suppress_flag = inst_record.find(".//suppress_from_publishing").text
    return suppress_flag

def get_other_institutions_suppress_flag(institution,ava_fields_list,log_module):
    """If other institutions are located under the record look at the suppressed_flag. If all the records have marked the record. Return true the record can be suppressed in t the NZ
    Else return False . If there is no other institutions return true.
    Args:
        institution(string): institution code
        ava_fields_list (array): list of xml object
        log_module(obj.): log instance
    Return:
        Bolean
    """
    processed_inst_list = []
    if not ava_fields_list :
        return True
    for ava_field in ava_fields_list :
        #Test if MMS_Id ans Institution code are present in node
        if ava_field.find(".//subfield[@code='a']") is None or ava_field.find(".//subfield[@code='0']") is None :
            continue
        institution_code = ava_field.find(".//subfield[@code='a']").text
        #Test if the institution location has already been treated
        if processed_inst_list.count(institution_code) >= 1:
            continue
        if institution_code[7:] == institution:
            continue
        mms_id = ava_field.find(".//subfield[@code='0']").text
        log_module.debug("{} --> {}".format(institution_code,mms_id))
        inst_record_supress_flag = get_record_supress_flag(institution_code[7:],mms_id,log_module)
        log_module.debug("Supprimé : {}".format(inst_record_supress_flag))
        if inst_record_supress_flag == 'false' :
            return False
        processed_inst_list.append(institution_code)
    return True    
    
    