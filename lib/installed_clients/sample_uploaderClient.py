# -*- coding: utf-8 -*-
############################################################
#
# Autogenerated by the KBase type compiler -
# any changes made here will be overwritten
#
############################################################

from __future__ import print_function
# the following is a hack to get the baseclient to import whether we're in a
# package or not. This makes pep8 unhappy hence the annotations.
try:
    # baseclient and this client are in a package
    from .baseclient import BaseClient as _BaseClient  # @UnusedImport
except ImportError:
    # no they aren't
    from baseclient import BaseClient as _BaseClient  # @Reimport


class sample_uploader(object):

    def __init__(
            self, url=None, timeout=30 * 60, user_id=None,
            password=None, token=None, ignore_authrc=False,
            trust_all_ssl_certificates=False,
            auth_svc='https://ci.kbase.us/services/auth/api/legacy/KBase/Sessions/Login',
            service_ver='dev',
            async_job_check_time_ms=100, async_job_check_time_scale_percent=150, 
            async_job_check_max_time_ms=300000):
        if url is None:
            raise ValueError('A url is required')
        self._service_ver = service_ver
        self._client = _BaseClient(
            url, timeout=timeout, user_id=user_id, password=password,
            token=token, ignore_authrc=ignore_authrc,
            trust_all_ssl_certificates=trust_all_ssl_certificates,
            auth_svc=auth_svc,
            async_job_check_time_ms=async_job_check_time_ms,
            async_job_check_time_scale_percent=async_job_check_time_scale_percent,
            async_job_check_max_time_ms=async_job_check_max_time_ms)

    def import_samples(self, params, context=None):
        """
        :param params: instance of type "ImportSampleInputs" -> structure:
           parameter "sample_set_ref" of String, parameter "sample_file" of
           String, parameter "workspace_name" of String, parameter
           "workspace_id" of Long, parameter "file_format" of String,
           parameter "description" of String, parameter "set_name" of String,
           parameter "header_row_index" of Long, parameter "output_format" of
           String, parameter "taxonomy_source" of String, parameter
           "num_otus" of Long, parameter "incl_seq" of Long, parameter
           "otu_prefix" of String
        :returns: instance of type "ImportSampleOutputs" -> structure:
           parameter "report_name" of String, parameter "report_ref" of
           String, parameter "sample_set" of type "SampleSet" -> structure:
           parameter "samples" of list of type "sample_info" -> structure:
           parameter "id" of type "sample_id", parameter "name" of String,
           parameter "description" of String, parameter "sample_set_ref" of
           String
        """
        return self._client.run_job('sample_uploader.import_samples',
                                    [params], self._service_ver, context)

    def generate_OTU_sheet(self, params, context=None):
        """
        :param params: instance of type "GenerateOTUSheetParams" (Generate a
           customized OTU worksheet using a SampleSet input to generate the
           appropriate columns.) -> structure: parameter "workspace_name" of
           String, parameter "workspace_id" of Long, parameter
           "sample_set_ref" of String, parameter "output_name" of String,
           parameter "output_format" of String, parameter "num_otus" of Long,
           parameter "taxonomy_source" of String, parameter "incl_seq" of
           Long, parameter "otu_prefix" of String
        :returns: instance of type "GenerateOTUSheetOutputs" -> structure:
           parameter "report_name" of String, parameter "report_ref" of String
        """
        return self._client.run_job('sample_uploader.generate_OTU_sheet',
                                    [params], self._service_ver, context)

    def update_sample_set_acls(self, params, context=None):
        """
        :param params: instance of type "update_sample_set_acls_params" ->
           structure: parameter "sample_set_ref" of String, parameter
           "new_users" of list of String, parameter "is_reader" of Long,
           parameter "is_writer" of Long, parameter "is_admin" of Long
        :returns: instance of type "update_sample_set_acls_output" ->
           structure: parameter "status" of String
        """
        return self._client.run_job('sample_uploader.update_sample_set_acls',
                                    [params], self._service_ver, context)

    def export_samples(self, params, context=None):
        """
        :param params: instance of type "ExportParams" (export function for
           samples) -> structure: parameter "input_ref" of String, parameter
           "file_format" of String
        :returns: instance of type "ExportOutput" -> structure: parameter
           "shock_id" of String
        """
        return self._client.run_job('sample_uploader.export_samples',
                                    [params], self._service_ver, context)

    def status(self, context=None):
        return self._client.run_job('sample_uploader.status',
                                    [], self._service_ver, context)
