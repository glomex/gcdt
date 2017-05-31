# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import codecs
import json
import os
import uuid

from botocore.exceptions import ClientError
from pybars import Compiler
from tabulate import tabulate


SWAGGER_FILE = 'swagger.yaml'
INVOKE_FUNCTION_ACTION = 'lambda:InvokeFunction'
AMAZON_API_PRINCIPAL = 'apigateway.amazonaws.com'


# WIP
def export_to_swagger(awsclient, api_name, stage_name, api_description,
                      lambdas, custom_hostname=False, custom_base_path=False):
    """Export the API design as swagger file. 
    
    :param api_name: 
    :param stage_name: 
    :param api_description: 
    :param lambdas: 
    :param custom_hostname: 
    :param custom_base_path: 
    """
    print('Exporting to swagger...')

    api = _api_by_name(awsclient, api_name)
    if api is not None:

        print(_json2table(api))
        api_id = api['id']
        client_api = awsclient.get_client('apigateway')
        template_variables = _template_variables_to_dict(
            client_api,
            api_name,
            api_description,
            stage_name,
            api_id,
            lambdas,
            custom_hostname,
            custom_base_path)
        content = _compile_template(SWAGGER_FILE, template_variables)
        swagger_file = open('swagger_export.yaml', 'w')

        swagger_file.write(content)
    else:
        print('API name unknown')


def list_apis(awsclient):
    """List APIs in account."""
    client_api = awsclient.get_client('apigateway')

    apis = client_api.get_rest_apis()['items']

    for api in apis:
        print(_json2table(api))


def deploy_api(awsclient, api_name, api_description, stage_name, api_key,
               lambdas):
    """Deploy API Gateway to AWS cloud.
    
    :param awsclient:
    :param api_name:
    :param api_description:
    :param stage_name: 
    :param api_key: 
    :param lambdas: 
    """
    if not _api_exists(awsclient, api_name):
        if os.path.isfile(SWAGGER_FILE):
            # this does an import from swagger file
            # the next step does not make sense since there is a check in
            # _import_from_swagger for if api is existent!
            # _create_api(api_name=api_name, api_description=api_description)
            _import_from_swagger(awsclient, api_name, api_description,
                                 stage_name, lambdas)
        else:
            print('No swagger file (%s) found' % SWAGGER_FILE)

        api = _api_by_name(awsclient, api_name)
        if api is not None:
            _ensure_lambdas_permissions(awsclient, lambdas, api)
            _create_deployment(awsclient, api_name, stage_name)
            _wire_api_key(awsclient, api_name, api_key, stage_name)
        else:
            print('API name unknown')
    else:
        if os.path.isfile(SWAGGER_FILE):
            _update_from_swagger(awsclient, api_name, api_description,
                                 stage_name, lambdas)
        else:
            _update_api()

        api = _api_by_name(awsclient, api_name)
        if api is not None:
            _ensure_lambdas_permissions(awsclient, lambdas, api)
            _create_deployment(awsclient, api_name, stage_name)
        else:
            print('API name unknown')


def delete_api(awsclient, api_name):
    """Delete the API.

    :param api_name:
    """
    client_api = awsclient.get_client('apigateway')

    print('deleting api: %s' % api_name)
    api = _api_by_name(awsclient, api_name)

    if api is not None:
        print(_json2table(api))

        response = client_api.delete_rest_api(
            restApiId=api['id']
        )

        print(_json2table(response))
    else:
        print('API name unknown')


def create_api_key(awsclient, api_name, api_key_name):
    """Create a new API key as reference for api.conf.

    :param api_name:
    :param api_key_name:
    :return: api_key
    """
    client_api = awsclient.get_client('apigateway')
    print('create api key: %s' % api_key_name)

    response = client_api.create_api_key(
        name=api_key_name,
        description='Created for ' + api_name,
        enabled=True
    )

    #print(_json2table(response))

    print('Add this api key \'%s\' to your api.conf' % response['id'])
    return response['id']


def delete_api_key(awsclient, api_key):
    """Remove API key.

    :param api_key:
    """
    client_api = awsclient.get_client('apigateway')
    print('delete api key: %s' % api_key)

    response = client_api.delete_api_key(
        apiKey=api_key
    )

    print(_json2table(response))


def list_api_keys(awsclient):
    """Print the defined API keys.
    """
    client_api = awsclient.get_client('apigateway')
    print('listing api keys')

    response = client_api.get_api_keys()['items']

    for item in response:
        print(_json2table(item))


def create_custom_domain(awsclient, api_name, api_target_stage,
                         api_base_path, domain_name, route_53_record,
                         ssl_cert, hosted_zone_id):
    """Add custom domain to your API.

    :param api_name:
    :param api_target_stage:
    :param api_base_path:
    :param domain_name:
    :param route_53_record:
    :param ssl_cert:
    :param hosted_zone_id:
    :return: exit_code
    """
    api_base_path = _basepath_to_string_if_null(api_base_path)
    api = _api_by_name(awsclient, api_name)

    if not api:
        print("Api %s does not exist, aborting..." % api_name)
        # exit(1)
        return 1

    domain = _custom_domain_name_exists(awsclient, domain_name)

    if not domain:
        response = _create_new_custom_domain(awsclient, domain_name,
                                             ssl_cert)
        cloudfront_distribution = response['distributionDomainName']
    else:
        cloudfront_distribution = domain['distributionDomainName']

    if _base_path_mapping_exists(awsclient, domain_name, api_base_path):
        _ensure_correct_base_path_mapping(awsclient, domain_name,
                                          api_base_path, api['id'],
                                          api_target_stage)
    else:
        _create_base_path_mapping(awsclient, domain_name, api_base_path,
                                  api_target_stage, api['id'])

    record_exists, record_correct = \
        _record_exists_and_correct(awsclient, hosted_zone_id,
                                   route_53_record,
                                   cloudfront_distribution)
    if record_correct:
        print('Route53 record correctly set: %s --> %s' % (route_53_record,
                                                           cloudfront_distribution))
    else:
        _ensure_correct_route_53_record(awsclient, hosted_zone_id,
                                        record_name=route_53_record,
                                        record_value=cloudfront_distribution)
        print('Route53 record set: %s --> %s' % (route_53_record,
                                                 cloudfront_distribution))
    return 0


def get_lambdas(awsclient, config, add_arn=False):
    """Get the list of lambda functions.

    :param config:
    :param add_arn:
    :return: list containing lambda entries
    """
    if 'lambda' in config:
        client_lambda = awsclient.get_client('lambda')
        lambda_entries = config['lambda'].get('entries', [])
        lmbdas = []
        for lambda_entry in lambda_entries:
            lmbda = {
                'name': lambda_entry.get('name', None),
                'alias': lambda_entry.get('alias', None),
                'swagger_ref': lambda_entry.get('swaggerRef', None)
            }
            if add_arn:
                response_lambda = client_lambda.get_function(
                    FunctionName=lmbda['name'])
                lmbda['arn'] = response_lambda['Configuration']['FunctionArn']
            lmbdas.append(lmbda)
        return lmbdas
    else:
        return []


def _import_from_swagger(awsclient, api_name, api_description, stage_name,
                         lambdas):
    client_api = awsclient.get_client('apigateway')

    print('Import from swagger file')

    api = _api_by_name(awsclient, api_name)
    if api is None:
        #print(_json2table(api))
        api_id = False
        template_variables = _template_variables_to_dict(
            client_api,
            api_name,
            api_description,
            stage_name,
            api_id,
            lambdas)
        swagger_body = _compile_template(SWAGGER_FILE,
                                         template_variables)
        response_swagger = client_api.import_rest_api(
            failOnWarnings=True,
            body=swagger_body
        )
        print(_json2table(response_swagger))
    else:
        print('API already taken')


def _update_from_swagger(awsclient, api_name, api_description, stage_name,
                         lambdas):
    client_api = awsclient.get_client('apigateway')

    print('update from swagger file')

    api = _api_by_name(awsclient, api_name)

    if api is not None:
        api_id = api['id']
        template_variables = _template_variables_to_dict(
            client_api,
            api_name,
            api_description,
            stage_name,
            api_id,
            lambdas)
        filled_swagger_file = _compile_template(SWAGGER_FILE,
                                                template_variables)

        response_swagger = client_api.put_rest_api(
            restApiId=api['id'],
            mode='overwrite',
            failOnWarnings=True,
            body=filled_swagger_file
        )
    else:
        print('API name unknown')

    print(_json2table(response_swagger))


def _create_api(awsclient, api_name, api_description):
    client_api = awsclient.get_client('apigateway')

    print('creating API')

    response = client_api.create_rest_api(
        name=api_name,
        description=api_description
    )

    print(_json2table(response))


def _wire_api_key(awsclient, api_name, api_key, stage_name):
    client_api = awsclient.get_client('apigateway')
    print('updating api key')

    api = _api_by_name(awsclient, api_name)

    if api is not None:

        response = client_api.update_api_key(
            apiKey=api_key,
            patchOperations=[
                {
                    'op': 'add',
                    'path': '/stages',
                    'value': "%s/%s" % (api['id'], stage_name)
                },
            ]
        )

        print(_json2table(response))
    else:
        print('API name unknown')


def _update_api():
    print('updating api. not supported now')


def _create_deployment(awsclient, api_name, stage_name):
    client_api = awsclient.get_client('apigateway')
    print('create deployment')

    api = _api_by_name(awsclient, api_name)

    if api is not None:

        response = client_api.create_deployment(
            restApiId=api['id'],
            stageName=stage_name,
            description='TO BE FILLED'
        )

        print(_json2table(response))
    else:
        print('API name unknown')


def _ensure_correct_route_53_record(awsclient, hosted_zone_id, record_name,
                                    record_value, record_type='CNAME'):
    client_route53 = awsclient.get_client('route53')
    response = client_route53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': (record_name + '.'),
                        'Type': record_type,
                        'ResourceRecords': [
                            {
                                'Value': record_value
                            }
                        ],
                        'TTL': 300
                    }
                }
            ]
        }
    )


def _ensure_correct_base_path_mapping(awsclient, domain_name, base_path,
                                      api_id,
                                      target_stage):
    client_api = awsclient.get_client('apigateway')
    mapping = client_api.get_base_path_mapping(domainName=domain_name,
                                               basePath=base_path)
    operations = []
    if not mapping['stage'] == target_stage:
        operations.append({
            'op': 'replace',
            'path': '/stage',
            'value': target_stage
        })
    if not mapping['restApiId'] == api_id:
        operations.append({
            'op': 'replace',
            'path': '/restApiId',
            'value': api_id
        })
    if operations:
        response = client_api.update_base_path_mapping(
            domainName=domain_name,
            basePath='(none)',
            patchOperations=operations)


def _base_path_mapping_exists(awsclient, domain_name, base_path):
    client_api = awsclient.get_client('apigateway')
    base_path_mappings = client_api.get_base_path_mappings(
        domainName=domain_name)
    mapping_exists = False
    if base_path_mappings.get('items'):
        for item in base_path_mappings['items']:
            if item['basePath'] == base_path:
                mapping_exists = True
    return mapping_exists


def _create_base_path_mapping(awsclient, domain_name, base_path, stage,
                              api_id):
    client_api = awsclient.get_client('apigateway')
    base_path_respone = client_api.create_base_path_mapping(
        domainName=domain_name,
        basePath=base_path,
        restApiId=api_id,
        stage=stage
    )


def _record_exists_and_correct(awsclient, hosted_zone_id,
                               target_route_53_record_name,
                               cloudfront_distribution):
    client_route53 = awsclient.get_client('route53')
    response = client_route53.list_resource_record_sets(
        HostedZoneId=hosted_zone_id
    )
    resource_records = response['ResourceRecordSets']
    record_exists = False
    record_correct = False
    for record in resource_records:
        if record['Name'] == (target_route_53_record_name + '.'):
            record_exists = True
            for value in record['ResourceRecords']:
                if value['Value'] == cloudfront_distribution:
                    record_correct = True
    return record_exists, record_correct


def _create_new_custom_domain(awsclient, domain_name, ssl_cert):
    client_api = awsclient.get_client('apigateway')
    response = client_api.create_domain_name(
        domainName=domain_name,
        certificateName=ssl_cert['name'],
        certificateBody=ssl_cert['body'],
        certificatePrivateKey=ssl_cert['private_key'],
        certificateChain=ssl_cert['chain']
    )
    return response


# original signature (fixed otherwise implementation makes no sense):
# def _template_variables_to_dict(api_name, api_description, api_target_stage,
#                                api_id=False, lambdas=[], custom_hostname=False,
#                                custom_base_path=False):
def _template_variables_to_dict(client_api, api_name, api_description,
                                api_target_stage, api_id=False, lambdas=[],
                                custom_hostname=None, custom_base_path=None):
    if lambdas:
        lambda_region, lambda_account_id = \
            _get_region_and_account_from_lambda_arn(lambdas[0].get('arn'))
    else:
        lambda_region = client_api.meta.region_name

    if custom_hostname:
        api_hostname = custom_hostname
        api_basepath = custom_base_path
    elif not api_id:  # case deploying new api, -> hostname exists
        api_hostname = False
        api_basepath = api_target_stage  #
    else:  # not using custom domain name
        api_hostname = api_id + '.execute-api.' + lambda_region + '.amazonaws.com'
        api_basepath = api_target_stage  #

    return_dict = {
        'apiName': api_name,
        'apiDescription': api_description,
        'apiBasePath': api_basepath
        # 'apiHostname': api_hostname  # or the next statement is dead!
    }
    if api_hostname:
        return_dict['apiHostname'] = api_hostname

    for lmbda in lambdas:
        if lmbda.get('arn'):
            lambda_uri = _arn_to_uri(lmbda['arn'], lmbda['alias'])
            return_dict.update({str(lmbda['swagger_ref']): lambda_uri})
    return return_dict


def _ensure_lambdas_permissions(awsclient, lambdas, api):
    client_lambda = awsclient.get_client('lambda')
    for lmbda in lambdas:
        _ensure_lambda_permissions(client_lambda, lmbda, api, )


def _ensure_lambda_permissions(client_lambda, lmbda, api):
    if not lmbda.get('arn'):
        lambda_name = lmbda.get('name', '(no name provided)')
        print('Lambda function {} could not be found'.format(lambda_name))
        return

    lambda_arn = lmbda.get('arn')
    lambda_alias = lmbda.get('alias')
    lambda_name = lmbda.get('name')

    lambda_region, lambda_account_id = \
        _get_region_and_account_from_lambda_arn(lambda_arn)

    source_arn = 'arn:aws:execute-api:{region}:{accountId}:{apiId}/*/*'.format(
        region=lambda_region,
        accountId=lambda_account_id,
        apiId=api['id']
    )

    if _invoke_lambda_permission_exists(client_lambda, lambda_arn, source_arn):
        print('API already has permission to invoke lambda {}'.format(
            lambda_name))
        return

    print('Adding lambda permission for API Gateway for lambda {}'.format(
        lambda_name))
    response = client_lambda.add_permission(
        FunctionName=lambda_name,
        StatementId=str(uuid.uuid1()),
        Action=INVOKE_FUNCTION_ACTION,
        Principal=AMAZON_API_PRINCIPAL,
        SourceArn=source_arn,
        Qualifier=lambda_alias
    )

    print(_json2table(json.loads(response['Statement'])))


def _invoke_lambda_permission_exists(client_lambda, lambda_arn, source_arn):
    policy_resource_arn = lambda_arn + ':ACTIVE'
    try:
        response = client_lambda.get_policy(FunctionName=policy_resource_arn)
    except ClientError:
        return False

    permissions = json.loads(response['Policy'])['Statement']
    return [
        p for p in permissions
        if p.get('Condition', {}).get('ArnLike', {}).get(
            'AWS:SourceArn') == source_arn
        and p.get('Action') == INVOKE_FUNCTION_ACTION
        and p.get('Effect') == 'Allow'
        and p.get('Principal', {}).get('Service') == AMAZON_API_PRINCIPAL
        ]


# TODO: possible to consolidate this with the one for ramuda?
def _json2table(data):
    filter_terms = ['ResponseMetadata']
    table = []
    try:
        for k, v in filter(lambda k, v: k not in filter_terms,
                           data.iteritems()):
            table.append([k, str(v)])
        return tabulate(table, tablefmt='fancy_grid')
    except Exception as e:
        return data


def _custom_domain_name_exists(awsclient, domain_name):
    client_api = awsclient.get_client('apigateway')
    try:
        domain = client_api.get_domain_name(domainName=domain_name)
    except ClientError as e:
        domain = None
        if e.response['Error']['Code'] == 'NotFoundException':
            pass
        else:
            raise
    return domain


def _api_exists(awsclient, api_name):
    api = _api_by_name(awsclient, api_name)

    if api is None:
        return False

    return True


def _api_by_name(awsclient, api_name):
    client_api = awsclient.get_client('apigateway')
    filtered_rest_apis = \
        list(filter(lambda api: True if api['name'] == api_name else False,
               client_api.get_rest_apis()['items']))
    if len(filtered_rest_apis) > 1:
        raise Exception(
            'more than one API with that name found. Clean up manually first')
    elif len(filtered_rest_apis) == 0:
        return None
    else:
        return filtered_rest_apis[0]


def _basepath_to_string_if_null(basepath):
    # None (empty basepath) defined as '(null)' in API Gateway
    if basepath is None or basepath == '':
        basepath = '(none)'
    return basepath


def _compile_template(swagger_template_file, template_params):
    compiler = Compiler()
    with codecs.open(swagger_template_file, 'r', 'utf-8') as f:
        template_file = f.read()
    template = compiler.compile(template_file)
    filled_template = template(template_params)
    return filled_template


def _get_region_and_account_from_lambda_arn(lambda_arn):
    lambda_region = lambda_arn.split(':')[3]
    lambda_account_id = lambda_arn.split(':')[4]
    return lambda_region, lambda_account_id


def _arn_to_uri(lambda_arn, lambda_alias):
    lambda_region, lambda_account_id = _get_region_and_account_from_lambda_arn(
        lambda_arn)
    arn_prefix = 'arn:aws:apigateway:' + lambda_region + \
                 ':lambda:path/2015-03-31/functions/'
    arn_suffix = '/invocations'
    return arn_prefix + lambda_arn + ':' + lambda_alias + arn_suffix
