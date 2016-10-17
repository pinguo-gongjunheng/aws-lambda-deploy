#!/usr/bin/python

import json
import os
import shutil
from distutils.dir_util import copy_tree

import boto3


def build_python(_config):
    print 'building...'
    s3_client = boto3.client('s3')
    if os.path.exists('target'):
        shutil.rmtree('target')
        os.mkdir('target')
        os.mkdir('target/staging')

    staging_path = 'target/staging/'
    copy_tree(os.path.join(_config['python_env'], 'lib/python2.7/site-packages/'), staging_path)
    copy_tree(_config['python_source'], staging_path)

    package_zip_path = 'target/' + '%s-%s' % (_config['id'], _config['version'])
    _file = shutil.make_archive(package_zip_path, 'zip', staging_path)
    print 'build output to [%s] uploading to s3 [%s/%s]' % (_file, _config['s3_bucket'], os.path.basename(_file))
    s3_client.upload_file(_file, _config['s3_bucket'], os.path.basename(_file))
    print 'build and upload completed'
    return _file


def deploy_lambda(_config, _package_file):
    lambda_client = boto3.client('lambda')
    exists_functions = lambda_client.list_functions()
    matched_function = filter(lambda x: x['FunctionName'] == _config['name'], exists_functions['Functions'])
    if len(matched_function) == 0:
        print 'create new function cause [%s] not exists' % _config['id']
        params = {
            'FunctionName': _config['name'],
            'Role': _config['role'],
            'Handler': _config['handler'],
            'Code': {
                'S3Bucket': _config['s3_bucket'],
                'S3Key': os.path.basename(_package_file)
            },
            'Description': _config['description'],
            'Timeout': _config['timeout'],
            'MemorySize': _config['memory_size'],
            'Publish': _config['publish']
        }

        if _config['schema'] == 'python':
            params['Runtime'] = 'python2.7'
        else:
            params['Runtime'] = 'java8'

        create_response = lambda_client.create_function(**params)
        print create_response
    else:
        print 'update exists function [%s]' % _config['id']
        update_response = lambda_client.update_function_code(
            FunctionName=_config['name'],
            S3Bucket=_config['s3_bucket'],
            S3Key=os.path.basename(_package_file),
            Publish=_config['publish']
        )
        print update_response


if __name__ == '__main__':
    try:
        with open('deploy.json') as f:
            config = json.loads(f.read())
            if config['schema'] == 'python':
                package_file = build_python(config)
            else:
                package_file = ''
            deploy_lambda(config, package_file)

    except IOError as e:
        print 'can not open [deploy.json] cause file broken or not found.'
