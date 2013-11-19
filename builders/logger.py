'''
Created on Sep 10, 2013

This module holds logger configuration for builders

@author: pupssman
'''

import logging

logger = logging.getLogger('builders')
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setLevel(logging.WARN)

logger.addHandler(handler)
