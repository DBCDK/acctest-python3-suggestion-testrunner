#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- mode: python -*-
"""
:mod:`suggestion_testrunner.resource_manager` -- Resource manager for suggestion
================================================================================

============================
Suggestion resource manager
============================

Resource Manager for suggestion-service/solr integration
testing.
"""
import hashlib
import logging
import os
import sys
import requests
import time

from os_python.common.utils.init_functions import NullHandler

from os_python.docker.docker_container import DockerContainer
from os_python.docker.docker_container import ContainerSuitePool

from configobj import ConfigObj


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))))
from acceptance_tester.abstract_testsuite_runner.resource_manager import AbstractResourceManager


# define logger
logger = logging.getLogger("dbc." + __name__)
logger.addHandler(NullHandler())

class ContainerPoolImpl(ContainerSuitePool):

    def create_suite(self, suite):
        suite_name = "_suggestion_%f" % time.time()
        corepo_solr = suite.create_container("corepo-solr",
                                             image_name=DockerContainer.secure_docker_image('corepo-indexer-solr-1.1'),
                                             name="corepo-solr" + suite_name,
                                             start_timeout=1200,
                                             mem_limit=2048)
        corepo_solr.start()

        opensearch = suite.create_container("opensearch",
                                            image_name=DockerContainer.secure_docker_image('opensearch-4.5'),
                                            environment_variables={"FEDORA":"",
                                                                   "AGENCY_PROFILE_FALLBACK": "test",
                                                                   "AGENCY_FALLBACK": 100200,
                                                                   "AGENCY_END_POINT": "http://openagency.addi.dk/test_2.34/",
                                                                   "SOLR": "http://%s:8983/solr/corepo/select" % corepo_solr.get_ip(),
                                                                   "HOLDINGS_ITEMS_INDEX": "",
                                                                   "RAW_RECORD_SOLR": "",
                                                                   "RAW_RECORD_CONTENT_SERVICE": "",
                                                                   "HOLDINGS_DB": "",
                                                                   "OPEN_FORMAT": ""},
                                            start_timeout=1200)
        opensearch.start()

        suggest_ranking = suite.create_container("suggest-ranking",
                                                 image_name=DockerContainer.secure_docker_image('suggest-ranking-service-1.0-snapshot'),
                                                 environment_variables={"JAVA_MAX_HEAP_SIZE": "2G",
                                                                        "LOG__dk_dbc": "TRACE"},
                                                 start_timeout=1200)
        suggest_ranking.start()

        suggest_service = suite.create_container("suggestion-service",
                                                 image_name=DockerContainer.secure_docker_image('suggestion-service-2.0-snapshot'),
                                                 environment_variables={"RANKING_URL":"http://%s:8080" % suggest_ranking.get_ip(),
                                                                        "SOLR_APPID": "acceptancetest-suggestion-service",
                                                                        "ANKIRO_URL": "http://ankiro-p01.dbc.dk/Services/SpellcheckWebService.svc",
                                                                        "CONTEXT_ROOT": "/",
                                                                        "OPENSEARCH_URL": "http://%s/opensearch/" % opensearch.get_ip(),
                                                                        "COREPO_SOLR_URL": "http://%s:8983/solr/corepo" % corepo_solr.get_ip(),
                                                                        "SERVER_NAME": "suggest",
                                                                        "LOG__dk_dbc": "TRACE",
                                                                        "JAVA_MAX_HEAP_SIZE": "2G"},
                                                 start_timeout=1200)
        suggest_service.start()

        opensearch.waitFor("resuming normal operations")
        suggest_ranking.waitFor("was successfully deployed")
        suggest_service.waitFor("was successfully deployed")
        corepo_solr.waitFor("Registered new searcher")

    def on_release(self, name, container):
        if name == "corepo-solr":
            url = "http://%s:8983/solr/corepo/update?stream.body=<delete><query>*:*</query></delete>&commit=true" % container.get_ip()
            requests.get(url)

class ResourceManager(AbstractResourceManager):

    def __init__(self, resource_folder, tests, use_preloaded, use_config, port_range=(11000, 12000)):
        self.tests = tests
        self.use_config_resources = use_config
        self.resource_config = ConfigObj(self.use_config_resources)
        self.container_pool = ContainerPoolImpl()

    def shutdown(self):
        self.container_pool.shutdown()
