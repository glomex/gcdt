# -*- coding: utf-8 -*-
"""Visualize cloudformation template."""
from __future__ import unicode_literals, print_function
import sys
from numbers import Number
import subprocess

from .utils import flatten  # python3 replacement for from compiler.ast import flatten

PY3 = sys.version_info[0] >= 3

if PY3:
    basestring = str
    unicode = str


# based on original version from https://github.com/benbc/cloud-formation-viz
# Author: Ben Butler-Cole
# License: MIT


# sample use:
# def main():
#    # python kumo_viz.py | dot -Tsvg -osample.svg
#    with open('ELBStickinessSample.template', 'r') as tfile:
#        template = json.loads(tfile.read())
#    cfn_viz(template, parameters={'KeyName': 'abc123'})


def cfn_viz(template, parameters={}, outputs={}, out=sys.stdout):
    """Render dot output for cloudformation.template in json format.
    """
    known_sg, open_sg = _analyze_sg(template['Resources'])
    (graph, edges) = _extract_graph(template.get('Description', ''),
                                    template['Resources'], known_sg, open_sg)
    graph['edges'].extend(edges)
    _handle_terminals(template, graph, 'Parameters', 'source', parameters)
    _handle_terminals(template, graph, 'Outputs', 'sink', outputs)
    graph['subgraphs'].append(_handle_pseudo_params(graph['edges']))

    _render(graph, out=out)


def _analyze_sg(elem):
    # helper to analyzse the security groups in the stack
    # returns known, open

    # "InstanceSecurityGroup" : {
    #    "Type" : "AWS::EC2::SecurityGroup",
    #    "Properties" : {
    #        "GroupDescription" :
    #            "Enable SSH access and HTTP access on the inbound port",
    #        "SecurityGroupIngress" : [ {
    #            "IpProtocol" : "tcp",
    #            "FromPort" : "22",
    #            "ToPort" : "22",
    #            "CidrIp" : { "Ref" : "SSHLocation"}
    #        },
    #            {
    #                "IpProtocol" : "tcp",
    #                "FromPort" : "80",
    #                "ToPort" : "80",
    #                "CidrIp" : "0.0.0.0/0"
    #            } ]
    #    }
    known_sg = []
    open_sg = []
    for item, details in elem.items():
        # item: ElasticLoadBalancer
        # details: {u'Type': u'AWS::ElasticLoadBalancing::LoadBalancer',
        #  u'Properties': {u'Scheme': u'internet-facing',...
        if 'Type' in details:
            resource_type = details['Type'].split('::')[-1]
            if resource_type and resource_type == 'SecurityGroup':
                known_sg.append(item)
                if 'Properties' in details:
                    properties = details['Properties']
                    if 'SecurityGroupIngress' in properties:
                        for sgi in properties['SecurityGroupIngress']:
                            if 'CidrIp' in sgi and sgi['CidrIp'] == '0.0.0.0/0'\
                                    and sgi['IpProtocol'].lower() != 'icmp':
                                open_sg.append(item)
    return known_sg, open_sg


def _handle_terminals(template, graph, name, rank, values={}):
    if name in template:
        (subgraph, edges) = _extract_graph_terminals(name, template[name], values)
        subgraph['rank'] = rank
        subgraph['style'] = 'filled,rounded'
        graph['subgraphs'].append(subgraph)
        graph['edges'].extend(edges)


def _handle_pseudo_params(edges):
    graph = {
        'name': 'Pseudo Parameters', 'nodes': [], 'edges': [],
        'subgraphs': []
    }
    graph['shape'] = 'ellipse'
    params = set()
    for e in edges:
        if e['from'].startswith(u'AWS::'):
            params.add(e['from'])
    graph['nodes'].extend({'name': n} for n in sorted(params))
    return graph


def _get_fillcolor(resource_type, properties, known_sg=[], open_sg=[]):
    """Determine fillcolor for resources (public ones in this case)
    """
    fillcolor = None
    # check security groups
    if 'SecurityGroups' in properties:
        # check for external security groups
        for sg in properties['SecurityGroups']:
            if 'Ref' in sg and (sg['Ref'] not in known_sg):
                fillcolor = 'yellow'
                break

        # check for open security groups
        for osg in open_sg:
            if {'Ref': osg} in properties['SecurityGroups']:
                fillcolor = 'red'
                break

    # LoadBalancer
    if resource_type == 'LoadBalancer':
        if ('Scheme' not in properties) or \
                        properties['Scheme'] == 'internet-facing':
            fillcolor = 'red'

    return fillcolor


def _extract_graph(name, elem, known_sg=[], open_sg=[]):
    graph = {'name': name, 'nodes': [], 'edges': [], 'subgraphs': []}
    edges = []
    for item, details in elem.items():
        # item: ElasticLoadBalancer
        # details: {u'Type': u'AWS::ElasticLoadBalancing::LoadBalancer',
        #  u'Properties': {u'Scheme': u'internet-facing',...
        node = {'name': item}
        if 'Type' in details:
            resource_type = details['Type'].split('::')[-1]
            if resource_type:
                node['type'] = resource_type
                if 'Properties' in details:
                    fillcolor = _get_fillcolor(resource_type,
                                               details['Properties'],
                                               known_sg, open_sg)
                    if fillcolor:
                        node['fillcolor'] = fillcolor
        graph['nodes'].append(node)
        edges.extend(flatten(_find_refs(item, details)))
    return graph, edges


def _extract_graph_terminals(name, elem, values={}):
    graph = {'name': name, 'nodes': [], 'edges': [], 'subgraphs': []}
    edges = []
    for item, details in elem.items():
        node = {'name': item}
        if item in values:
            node['value'] = values[item]
        graph['nodes'].append(node)
        edges.extend(sorted(flatten(_find_refs(item, details))))
    return graph, edges


def _find_refs(context, elem):
    if isinstance(elem, dict):
        refs = []
        for k, v in elem.items():
            if unicode(k) == unicode('Ref'):
                assert isinstance(v, basestring), 'Expected a string: %s' % v
                refs.append({'from': v, 'to': context})
            elif unicode(k) == unicode('Fn::GetAtt'):
                assert isinstance(v, list), 'Expected a list: %s' % v
                refs.append({'from': v[0], 'to': context})
            else:
                refs.extend(_find_refs(context, v))
        return refs
    elif isinstance(elem, list):
        return list(map(lambda e: _find_refs(context, e), elem))
    elif isinstance(elem, basestring):
        return []
    elif isinstance(elem, bool):
        return []
    elif isinstance(elem, Number):
        return []
    else:
        raise AssertionError('Unexpected type: %s' % elem)


def _render(graph, subgraph=False, out=sys.stdout):
    def _render_node(n):
        # helper to render a node (this adds type and fillcolor)
        # styles here: http://www.graphviz.org/doc/info/attrs.html#d:fillcolor
        if 'fillcolor' in n:
            # fillcolor ON
            print('node [style="filled"];', file=out)
            print('node [fillcolor="%s"]' % n['fillcolor'], file=out)
        if 'value' in n:
            # use HTML labels:
            # http://stackoverflow.com/questions/19280229/graphviz-putting-a-caption-on-a-node-in-addition-to-a-label
            print('"%s"[label=<%s<BR /><FONT POINT-SIZE="8">[=%s]</FONT>>]' %
                  (n['name'], n['name'], n['value']), file=out)
        elif 'type' in n:
            print('"%s"[label=<<FONT POINT-SIZE="8">[%s]</FONT><BR />%s>]' %
                  (n['name'], n['type'], n['name']), file=out)
        else:
            print('"%s"' % n['name'], file=out)
        if 'fillcolor' in n:
            # fillcolor OFF
            print('node [style=""];', file=out)
            print('node [fillcolor=""]', file=out)

    if subgraph:
        print('subgraph "%s" {' % graph['name'], file=out)
    else:
        print('digraph "%s" {' % graph['name'], file=out)
    print('labeljust=l;', file=out)
    print('node [shape={}];'.format(graph.get('shape', 'box')), file=out)
    if 'style' in graph:
        print('node [style="%s"]' % graph['style'], file=out)
    if 'rank' in graph:
        print('rank=%s' % graph['rank'], file=out)
    for node in graph['nodes']:
        _render_node(node)
    for s in graph['subgraphs']:
        _render(s, True, out)
    for e in graph['edges']:
        print('"%s" -> "%s";' % (e['from'], e['to']), file=out)
    print('}', file=out)


def svg_output(dotfile, outfile='cloudformation.svg'):
    """Render template into svg file using the dot command (must be installed).

    :param dotfile: path to the dotfile
    :param outfile: filename for the output file
    :return:
    """
    try:
        cmd = ['dot', '-Tsvg', '-o' + outfile, dotfile]
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            '\033[01;31mError running command: %s resulted in the ' % e.cmd +
            'following error: \033[01;32m %s' % e.output)
        return 1

    return 0
