
import errno
import logging
import os
import pandas as pd
from xlrd.biffh import XLRDError
import uuid

from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.KBaseReportClient import KBaseReport

from FunctionalProfileUtil.Utils.SampleServiceUtil import SampleServiceUtil

DATA_EPISTEMOLOGY = ['measured', 'asserted', 'predicted']
DEFAULT_PROFILE_NAME = ['pathway', 'EC', 'KO']


class ProfileImporter:

    @staticmethod
    def _mkdir_p(path):
        """
        _mkdir_p: make directory for given path
        """
        if not path:
            return
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    @staticmethod
    def _validate_params(params, expected, opt_param=set()):
        """Validates that required parameters are present. Warns if unexpected parameters appear"""
        expected = set(expected)
        opt_param = set(opt_param)
        pkeys = set(params)
        if expected - pkeys:
            raise ValueError("Required keys {} not in supplied parameters"
                             .format(", ".join(expected - pkeys)))
        defined_param = expected | opt_param
        for param in params:
            if param not in defined_param:
                logging.warning("Unexpected parameter {} supplied".format(param))

    @staticmethod
    def _file_to_df(file_path):
        logging.info('start parsing file content to data frame')

        try:
            df = pd.read_excel(file_path, sheet_name='data', index_col=0)

        except XLRDError:
            try:
                df = pd.read_excel(file_path, index_col=0)
                logging.warning('WARNING: A sheet named "data" was not found in the attached file,'
                                ' proceeding with the first sheet as the data sheet.')

            except XLRDError:

                try:
                    reader = pd.read_csv(file_path, sep=None, iterator=True)
                    inferred_sep = reader._engine.data.dialect.delimiter
                    df = pd.read_csv(file_path, sep=inferred_sep, index_col=0)
                except Exception:
                    err_msg = 'Cannot parse file. Please provide valide tsv, excel or csv file'
                    raise ValueError(err_msg)

        df.index = df.index.astype('str')
        df.columns = df.columns.astype('str')

        # fill NA with "None" so that they are properly represented as nulls in the KBase Object
        df = df.where((pd.notnull(df)), None)

        df = df.applymap(str)

        return df

    def _save_func_profile(self, workspace_id, func_profile_data, func_profile_obj_name):
        logging.info('start saving FunctionalProfile object: {}'.format(func_profile_obj_name))
        info = self.dfu.save_objects({
            "id": workspace_id,
            "objects": [{
                "type": "KBaseFunctionalProfile.FunctionalProfile",
                "data": func_profile_data,
                "name": func_profile_obj_name
            }]
        })[0]

        return "%s/%s/%s" % (info[6], info[0], info[4])

    def _gen_func_profile_report(self, func_profile_ref, workspace_id):
        logging.info('start generating report')

        objects_created = [{'ref': func_profile_ref, 'description': 'FunctionalProfile Object'}]

        report_params = {'message': '',
                         'objects_created': objects_created,
                         'workspace_id': workspace_id,
                         'report_object_name': 'import_func_profile_' + str(uuid.uuid4())}

        kbase_report_client = KBaseReport(self.callback_url, token=self.token)
        output = kbase_report_client.create_extended_report(report_params)

        report_output = {'report_name': output['name'], 'report_ref': output['ref']}

        return report_output

    def _get_ids_from_amplicon_set(self, amplicon_set_ref):
        logging.info('start retrieving OTU ids from amplicon set')

        amplicon_set_data = self.dfu.get_objects(
                                            {'object_refs': [amplicon_set_ref]})['data'][0]['data']

        amplicons = amplicon_set_data.get('amplicons')

        return amplicons.keys()

    def _build_profile_table(self, profile_file_path, data_ids, staging_file=False):

        if not profile_file_path:
            raise ValueError('Missing profile file path')

        logging.info('start reading {}'.format(os.path.basename(profile_file_path)))
        if staging_file:
            logging.info('start downloading staging file')
            download_staging_file_params = {'staging_file_subdir_path': profile_file_path}
            profile_file_path = self.dfu.download_staging_file(
                                                download_staging_file_params).get('copy_file_path')

        df = self._file_to_df(profile_file_path)

        # check profile file has all item ids from sample/amplicon set object
        unmatched_ids = set(data_ids) - set(df.columns)
        if unmatched_ids:
            msg = 'Found some unmatched set data ids in profile file columns\n{}'.format(
                                                                                    unmatched_ids)
            logging.warning(msg)
            df = df.T
            unmatched_ids = set(data_ids) - set(df.columns)
            if unmatched_ids:
                msg = 'Found some unmatched set data ids in profile file rows\n{}'.format(
                                                                                    unmatched_ids)
                logging.warning(msg)
                err_msg = 'Profile file does not contain all data ids from sample or amplicon set'
                raise ValueError(err_msg)

        profile_data = {'row_ids': df.index.tolist(),
                        'col_ids': df.columns.tolist(),
                        'values': df.values.tolist()}

        return profile_data

    def _fetch_existing_profile_names(self, profile):

        existing_profile_names = list()
        for default_name in DEFAULT_PROFILE_NAME:
            if profile.get(default_name):
                existing_profile_names.append(default_name)

        custom_profile_names = profile.get('custom_profiles', {}).keys()

        existing_profile_names.extend(custom_profile_names)

        logging.info('Found existing profiles: {}'.format(existing_profile_names))

        return existing_profile_names

    def _create_profile_data(self, profile_table, data_ids, staging_file=False):
        profile = dict()

        data_epistemology = profile_table.get('data_epistemology')

        if data_epistemology:
            data_epistemology = data_epistemology.lower()
            if data_epistemology not in DATA_EPISTEMOLOGY:
                err_msg = 'Data epistemology can only be one of {}'.format(DATA_EPISTEMOLOGY)
                raise ValueError(err_msg)

        profile['data_epistemology'] = data_epistemology
        for key in ['epistemology_method', 'description']:
            profile[key] = profile_table.get(key)

        profile_file_path = profile_table.get('profile_file_path')
        profile_data = self._build_profile_table(profile_file_path, data_ids,
                                                 staging_file=staging_file)

        profile['profile_data'] = profile_data

        return profile

    def _build_profile_data(self, profiles, data_ids, staging_file=False):
        logging.info('start building profile data')

        gen_profile_data = dict()
        for profile_name, profile_table in profiles.items():

            data_epistemology = profile_table.get('data_epistemology')

            if data_epistemology:
                data_epistemology = data_epistemology.lower()
                if data_epistemology not in DATA_EPISTEMOLOGY:
                    err_msg = 'Data epistemology can only be one of {}'.format(DATA_EPISTEMOLOGY)
                    raise ValueError(err_msg)

            epistemology_method = profile_table.get('epistemology_method')
            description = profile_table.get('description')
            profile_file_path = profile_table.get('profile_file_path')

            logging.info('start building profile table for {}'.format(profile_name))
            profile_data = self._build_profile_table(profile_file_path, data_ids,
                                                     staging_file=staging_file)

            if profile_name in DEFAULT_PROFILE_NAME:
                gen_profile_data[profile_name] = {'data_epistemology': data_epistemology,
                                                  'epistemology_method': epistemology_method,
                                                  'description': description,
                                                  'profile_data': profile_data}
            else:
                if not gen_profile_data.get('custom_profiles'):
                    gen_profile_data['custom_profiles'] = dict()
                gen_profile_data['custom_profiles'][profile_name] = {
                                                        'data_epistemology': data_epistemology,
                                                        'epistemology_method': epistemology_method,
                                                        'description': description,
                                                        'profile_data': profile_data}

        return gen_profile_data

    def _update_func_profile(self, func_profile_data, community_profile, organism_profile,
                             staging_file=False, upsert=False):

        ori_matrix_ref = func_profile_data['original_matrix_ref']
        ori_community_profile = func_profile_data.get('community_profile', dict())
        ori_organism_profile = func_profile_data.get('organism_profile', dict())

        ori_community_profile_names = self._fetch_existing_profile_names(ori_community_profile)
        ori_organism_profile_names = self._fetch_existing_profile_names(ori_organism_profile)

        for profile_name, profile_table in community_profile.items():
            logging.info('Start updating community profile')
            if ori_community_profile and profile_name in ori_community_profile_names and not upsert:
                raise ValueError('Profile [{}] already exists. Please set upsert to True.')

            if not ori_community_profile:
                matrix_data = self.dfu.get_objects({'object_refs': [ori_matrix_ref]})['data'][0]['data']
                sample_set_ref = matrix_data.get('sample_set_ref')
                if not sample_set_ref:
                    raise ValueError('Cannot find sample set assocaited with original matrix')
                func_profile_data['community_profile'] = {'sample_set_ref': sample_set_ref}

                ori_community_profile = func_profile_data.get('community_profile')

            sample_set_ref = ori_community_profile.get('sample_set_ref')
            data_ids = self.sampleservice_util.get_ids_from_samples(sample_set_ref)
            profile_data = self._create_profile_data(profile_table, data_ids,
                                                     staging_file=staging_file)
            if profile_name in DEFAULT_PROFILE_NAME:
                ori_community_profile[profile_name] = profile_data
            else:
                custom_profiles = ori_community_profile.get('custom_profiles')
                if custom_profiles:
                    custom_profiles[profile_name] = profile_data
                else:
                    # create custom_profiles
                    ori_community_profile['custom_profiles'] = dict()
                    ori_community_profile['custom_profiles'][profile_name] = profile_data

        for profile_name, profile_table in organism_profile.items():
            logging.info('Start updating organism profile')
            if ori_organism_profile and profile_name in ori_organism_profile_names and not upsert:
                raise ValueError('Profile [{}] already exists. Please set upsert to True.')

            if not ori_organism_profile:
                matrix_data = self.dfu.get_objects({'object_refs': [ori_matrix_ref]})['data'][0]['data']
                amplicon_set_ref = matrix_data.get('amplicon_set_ref')
                if not amplicon_set_ref:
                    raise ValueError('Cannot find amplicon set assocaited with original matrix')
                func_profile_data['organism_profile'] = {'amplicon_set_ref': amplicon_set_ref}

                ori_organism_profile = func_profile_data.get('organism_profile')

            amplicon_set_ref = ori_organism_profile.get('amplicon_set_ref')
            data_ids = self._get_ids_from_amplicon_set(amplicon_set_ref)
            profile_data = self._create_profile_data(profile_table, data_ids,
                                                     staging_file=staging_file)
            if profile_name in DEFAULT_PROFILE_NAME:
                ori_organism_profile[profile_name] = profile_data
            else:
                custom_profiles = ori_organism_profile.get('custom_profiles')
                if custom_profiles:
                    custom_profiles[profile_name] = profile_data
                else:
                    # create custom_profiles
                    ori_community_profile['custom_profiles'] = dict()
                    ori_organism_profile['custom_profiles'][profile_name] = profile_data

        return func_profile_data

    def _gen_func_profile(self, original_matrix_ref, community_profile, organism_profile,
                          staging_file=False):
        func_profile_data = dict()

        if not original_matrix_ref:
            raise ValueError('Missing original matrix object reference')
        func_profile_data['original_matrix_ref'] = original_matrix_ref

        if community_profile:
            logging.info('start building community profile')
            sample_set_ref = community_profile.get('sample_set_ref')
            if not sample_set_ref:
                raise ValueError('Missing sample_set_ref from community profile')
            data_ids = self.sampleservice_util.get_ids_from_samples(sample_set_ref)

            comm_profile = self._build_profile_data(community_profile.get('profiles'),
                                                    data_ids,
                                                    staging_file=staging_file)
            comm_profile['sample_set_ref'] = sample_set_ref

            func_profile_data['community_profile'] = comm_profile

        if organism_profile:
            logging.info('start building organism profile')
            amplicon_set_ref = organism_profile.get('amplicon_set_ref')
            if not amplicon_set_ref:
                raise ValueError('Missing amplicon_set_ref from organism profile')

            data_ids = self._get_ids_from_amplicon_set(amplicon_set_ref)

            org_profile = self._build_profile_data(organism_profile.get('profiles'),
                                                   data_ids,
                                                   staging_file=staging_file)

            org_profile['amplicon_set_ref'] = amplicon_set_ref

            func_profile_data['organism_profile'] = org_profile

        return func_profile_data

    def __init__(self, config):
        self.callback_url = config['SDK_CALLBACK_URL']
        self.scratch = config['scratch']
        self.token = config['KB_AUTH_TOKEN']
        self.dfu = DataFileUtil(self.callback_url)
        self.sampleservice_util = SampleServiceUtil(config)

        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)

    def import_func_profile(self, params):

        logging.info("start importing FunctionalProfile with params:{}".format(params))

        self._validate_params(params, ('workspace_id',
                                       'func_profile_obj_name',
                                       'original_matrix_ref'))

        workspace_id = params.get('workspace_id')
        func_profile_obj_name = params.get('func_profile_obj_name')
        staging_file = params.get('staging_file', False)

        original_matrix_ref = params.get('original_matrix_ref')
        community_profile = params.get('community_profile')
        organism_profile = params.get('organism_profile')

        func_profile_data = self._gen_func_profile(original_matrix_ref,
                                                   community_profile,
                                                   organism_profile,
                                                   staging_file=staging_file)

        func_profile_ref = self._save_func_profile(workspace_id,
                                                   func_profile_data,
                                                   func_profile_obj_name)

        returnVal = {'func_profile_ref': func_profile_ref}

        return returnVal

    def insert_func_profile(self, params):

        logging.info("start updating FunctionalProfile with params:{}".format(params))

        self._validate_params(params, ('workspace_id',
                                       'functional_profile_ref'))

        workspace_id = params.get('workspace_id')
        func_profile_ref = params.get('functional_profile_ref')
        staging_file = params.get('staging_file', False)
        upsert = params.get('upsert', False)

        community_profile = params.get('community_profile', dict())
        organism_profile = params.get('organism_profile', dict())

        func_profile_obj = self.dfu.get_objects({'object_refs': [func_profile_ref]})['data'][0]
        func_profile_info = func_profile_obj['info']
        func_profile_obj_name = func_profile_info[1]
        func_profile_data = func_profile_obj['data']

        func_profile_data = self._update_func_profile(func_profile_data,
                                                      community_profile,
                                                      organism_profile,
                                                      staging_file=staging_file,
                                                      upsert=upsert)

        func_profile_ref = self._save_func_profile(workspace_id,
                                                   func_profile_data,
                                                   func_profile_obj_name)

        returnVal = {'func_profile_ref': func_profile_ref}

        return returnVal

    def narrative_import_func_profile(self, params):

        workspace_id = params.get('workspace_id')
        import_params = {'workspace_id': workspace_id,
                         'func_profile_obj_name': params.get('func_profile_obj_name'),
                         'original_matrix_ref': params.get('original_matrix_ref'),
                         'staging_file': True}

        community_profile = {'sample_set_ref': params.get('sample_set_ref'),
                             'profiles': dict()}
        organism_profile = {'amplicon_set_ref': params.get('amplicon_set_ref'),
                            'profiles': dict()}

        input_community_profile = params.get('community_profile')
        input_organism_profile = params.get('organism_profile')

        for profile in input_community_profile:
            profile_name = profile.get('community_profile_name')

            community_profile['profiles'][profile_name] = {
                            'data_epistemology': profile.get('community_data_epistemology'),
                            'epistemology_method': profile.get('community_epistemology_method'),
                            'description': profile.get('community_description'),
                            'profile_file_path': profile.get('community_profile_file_path')}

        for profile in input_organism_profile:
            profile_name = profile.get('organism_profile_name')

            organism_profile['profiles'][profile_name] = {
                            'data_epistemology': profile.get('organism_data_epistemology'),
                            'epistemology_method': profile.get('organism_epistemology_method'),
                            'description': profile.get('organism_description'),
                            'profile_file_path': profile.get('organism_profile_file_path')}

        import_params['community_profile'] = community_profile
        import_params['organism_profile'] = organism_profile

        func_profile_ref = self.import_func_profile(import_params)['func_profile_ref']

        returnVal = {'func_profile_ref': func_profile_ref}

        report_output = self._gen_func_profile_report(func_profile_ref, workspace_id)
        returnVal.update(report_output)

        return returnVal

    def narrative_insert_func_profile(self, params):

        workspace_id = params.get('workspace_id')
        insert_params = {'workspace_id': workspace_id,
                         'functional_profile_ref': params.get('functional_profile_ref'),
                         'upsert': params.get('upsert', False),
                         'staging_file': True}

        community_profile = dict()
        organism_profile = dict()

        input_community_profile = params.get('community_profile')
        input_organism_profile = params.get('organism_profile')

        for profile in input_community_profile:
            profile_name = profile.get('community_profile_name')

            community_profile[profile_name] = {
                            'data_epistemology': profile.get('community_data_epistemology'),
                            'epistemology_method': profile.get('community_epistemology_method'),
                            'description': profile.get('community_description'),
                            'profile_file_path': profile.get('community_profile_file_path')}

        for profile in input_organism_profile:
            profile_name = profile.get('organism_profile_name')

            organism_profile[profile_name] = {
                            'data_epistemology': profile.get('organism_data_epistemology'),
                            'epistemology_method': profile.get('organism_epistemology_method'),
                            'description': profile.get('organism_description'),
                            'profile_file_path': profile.get('organism_profile_file_path')}

        insert_params['community_profile'] = community_profile
        insert_params['organism_profile'] = organism_profile

        func_profile_ref = self.insert_func_profile(insert_params)['func_profile_ref']

        returnVal = {'func_profile_ref': func_profile_ref}

        report_output = self._gen_func_profile_report(func_profile_ref, workspace_id)
        returnVal.update(report_output)

        return returnVal