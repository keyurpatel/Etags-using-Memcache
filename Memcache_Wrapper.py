"""
__author__ = 'Keyur Patel'
__Purpose__ = This Memcache wrapper is designed to work close with google memcache with more developer's custom way.
It has two classes BaseClass (MemCache_Wrapper) and DerivedClass (Etags_Wrapper).
MemCache_Wrapper - Contains custom memchace methods.
Etags_Wrapper - This derived class generates the md5 hash etags and does logic of returning 304 status or cache data.
"""

import datetime
import hashlib
import logging


from google.appengine.api import memcache

#Date Formats
HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S %Z"
REMOVE_MILLI_SEC = "%Y-%m-%d %H:%M:%S"

"""
BaseClass:
1) Extended the GAE memcache functionality to use all the memcache methods in customized fashion.
"""
class Memcache_Wrapper(memcache.Client):

    """
        add(key, value, time=0, min_compress_len=0, namespace=None)
    """
    def add(self, key, value, time=0, min_compress_len=0, namespace=None):
        #object of Etags_Wrapper
        ew = Etags_Wrapper()
        #Actual Json dump
        memcache.add(key,value,time)

        #generate Last modified datetime for etags
        last_mod_date_key = key + "_lastmoddate"
        memcache.add(last_mod_date_key,str(datetime.datetime.utcnow().strftime(REMOVE_MILLI_SEC)),time)

        #generate etag # value and add it to memcache
        hash_etagsvalue = ew.generate_etags(value)
        hash_etagskey = key + "_etags"
        memcache.add(hash_etagskey,hash_etagsvalue,time)
        return


    """
        set(key, value, time=0, min_compress_len=0, namespace=None)
    """
    def set(self, key, value, time=0, min_compress_len=0, namespace=None):
        #object of Etags_Wrapper
        ew = Etags_Wrapper()
        #Actual Json dump
        memcache.set(key,value,time)

        #generate Last modified datetime for etags
        last_mod_date_key = key + "_lastmoddate"
        memcache.set(last_mod_date_key,str(datetime.datetime.utcnow().strftime(REMOVE_MILLI_SEC)),time)

        #generate etag # value and add it to memcache
        hash_etagsvalue = ew.generate_etags(value)
        hash_etagskey = key + "_etags"
        memcache.set(hash_etagskey,hash_etagsvalue,time)
        return

    """
        get(key, namespace=None, for_cas=False)
    """
    def get(self,key, namespace=None, for_cas=False):
        return memcache.get(key)

    """
    delete(key, seconds=0, namespace=None)
    """
    def delete(self,key, seconds=0, namespace=None):
        memcache.delete(key,seconds,namespace)

        last_mod_date_key = key + "_lastmoddate"
        memcache.delete(last_mod_date_key,seconds,namespace)

        hash_etagskey = key + "_etags"
        memcache.delete(hash_etagskey,seconds,namespace)
        return

"""
Derived Class:
1) Generates the etags hash value
2) returns the 304
3) adds the etag and last-modified date in response header
"""

class Etags_Wrapper(Memcache_Wrapper):
    def generate_etags(self,etagkey):
        hash_value = hashlib.md5(str(etagkey)).hexdigest()
        return hash_value


    def set_etags_header(self, etagkey, response):
        last_mod_date_key = etagkey + "_lastmoddate"
        hash_etagkey =  etagkey+"_etags"
        response.headers['Last-Modified'] = memcache.get(last_mod_date_key) or ""
        response.headers['ETag'] = memcache.get(hash_etagkey) or ""
        return response

    def get_etags(self,etagkey,headers):
        """
        #loop to check the header contents.
        for e in headers:
            #self.response.write(e + "<br />")
            logging.info("Header info - " + e + " value - "+ headers[e] +"<br />")
        """
        m = Memcache_Wrapper()

        etags_value = ['0']
        client_lastmodedate = ""

        hash_etagkey = etagkey+"_etags"
        hash_etagsvalue = m.get(hash_etagkey) # value from the cache

        last_mod_date_key = etagkey + "_lastmoddate"
        lastmoddate_value = m.get(last_mod_date_key) # value from the cache for lastmoddate

        # value from the header
        if 'If-None-Match' in headers:
            etags_value = [x.strip('" ') for x in headers['If-None-Match'].split(',')]
        if 'If-Modified-Since' in headers:
            client_lastmodedate = str(datetime.datetime.strptime(headers['If-Modified-Since'],HTTP_DATE_FMT))
        if etags_value[0] == hash_etagsvalue and client_lastmodedate == lastmoddate_value:
            return True
        else:
            return False
