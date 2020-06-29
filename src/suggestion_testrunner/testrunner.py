#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
:mod:`suggestion_testrunner.testrunner` -- Testrunner for suggestion
====================================================================

======================
Suggestion Testrunner
======================

This class executes xml test files of type 'suggestion'.
"""
import logging
import os
import shutil
import subprocess
import getpass
import time
#import zipfile
import socket
import struct
import array
import fcntl
import time

from nose.tools import nottest
from os_python.common.utils.init_functions import NullHandler

from acceptance_tester.abstract_testsuite_runner.test_runner import TestRunner as AbstractTestRunner

from os_python.solr.solr_parser import SolrParser
from os_python.connectors.suggestion import SuggestionService
from os_python.connectors.solr import Solr
from os_python.suggestionservice.suggestion_parser import SuggestionParser

# define logger
logger = logging.getLogger("dbc." + __name__)
logger.addHandler(NullHandler())


class TestRunner(AbstractTestRunner):

    @nottest
    def run_test(self, test_xml, build_folder, resource_manager):
        """
        Runs a 'fcrepo-solr' test.

        This method runs a test and puts the result into the
        failure/error lists accordingly.

        :param test_xml:
            Xml object specifying test.
        :type test_xml:
            lxml.etree.Element
        :param build_folder:
            Folder to use as build folder.
        :type build_folder:
            string
        :param resource_manager:
            Class used to secure reources.
        :type resource_manager:
            class that inherits from
            acceptance_tester.abstract_testsuite_runner.resource_manager

        """

        container_suite = resource_manager.container_pool.take(log_folder=self.logfolder)
        try:
            corepo_solr = container_suite.get("corepo-solr", build_folder)
            suggest_ranking = container_suite.get("suggest-ranking", build_folder)
            suggest_service = container_suite.get("suggestion-service", build_folder)

            # connectors
            suggestion_service_connector = SuggestionService("http://%s:8080" % suggest_service.get_ip(), "")
            solr_connector = Solr("http://%s:8983/solr" % corepo_solr.get_ip(), build_folder)

            ### Setup parsers
            self.parser_functions.update(SolrParser(self.base_folder, solr_connector).parser_functions)
            self.parser_functions.update(SuggestionParser(self.base_folder, suggestion_service_connector).parser_functions)

            ### run the test
            self.parse(test_xml)

        except Exception as err:
            logger.error( "Caught error during testing: %s"%str(err))
            raise

        finally:
            resource_manager.container_pool.release(container_suite)
