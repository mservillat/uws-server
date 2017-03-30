#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2016 by Mathieu Servillat
# Licensed under MIT (https://github.com/mservillat/uws-server/blob/master/LICENSE)
"""
Interfaces between UWS server and job description
"""

import collections
import inspect
import copy
import lxml.etree as ETree
from settings import *


# ---------
# jdl.content structure (class or dict?)

# job.jobname
'''
jdl.content = {
    'name': 'test',
    'label': 'test label',             # add
    'description': 'test description',
    'version': '1.2',
    'group': '',
    'job_type': '',
    'job_subtype': '',
    'doculink': '',                    # 'url' --> 'doculink'
    'contact_name': 'contact name',
    'contact_affil': '',               # remove...
    'contact_email': 'contact@email.com',
    'parameters': {},
    'results': {},
    'used': {},                        # add
    'executionduration': 1,
    'quote': 1,
}
parameters[pname] = {
    'type': p.get('type'),             # --> should be changed to 'datatype'
    'required': p.get('required'),     # type="no_query" in VOTable
    'default': p.get('default'),       # value in VOTable
    'unit': p.get('default'),          # add
    'ucd': p.get('default'),           # add
    'utype': p.get('default'),         # add
    'min': p.get('default'),           # add
    'max': p.get('default'),           # add
    'options': p.get('default'),       # add
    'description': list(p)[0].text,
}
results[rname] = {
    'default': r.get('default'),
    'content_type': r.get('content_type'),
    'description': list(r)[0].text,
}
used[pname] = {                        # add!
    'default': r.get('default'),
    'content_type': p.get('type'),     # xtype in VOTable (?)
    'description': list(r)[0].text,
}
'''

# ---------
# Job Description Language


class JDLFile(object):
    """
    Manage job description. This class defines required functions executed
    by the UWS server: save(), read().
    """
    content = {}
    extension = ''
    jdl_path = '.'

    def _get_filename(self, jobname):
        fn = '{}/{}{}'.format(self.jdl_path, jobname, self.extension)
        logger.info('JDL filename: ' + fn)
        return fn

    def save(self, jobname):
        """Save job description to file"""
        pass

    def read(self, jobname):
        """Read job description from file"""
        pass


class VOTFile(JDLFile):

    datatype_vo2xs = {
        "boolean": 'xs:boolean',
        "unsignedByte": 'xs:unsignedByte',
        "short": 'xs:short',
        "int": 'xs:integer',
        "long": 'xs:long',
        "char": 'xs:string',
        "float": 'xs:float',
        "double": 'xs:double'
    }
    datatype_xs2vo = {
        "xs:boolean": 'boolean',
        "xs:unsignedByte": 'unsignedByte',
        "xs:short": 'short',
        "xs:int": 'int',
        "xs:integer": 'int',
        "xs:long": 'long',
        "xs:string": 'char',
        "xs:float": 'float',
        "xs:double": 'double',
        'xs:anyURI': 'char'
    }

    def __init__(self, jdl_path=JDL_PATH):
        self.extension = '_vot.xml'
        self.jdl_path = jdl_path
        self.xmlns_uris = {
            'xmlns': 'http://www.ivoa.net/xml/VOTable/v1.3',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation':
                'http://www.ivoa.net/xml/VOTable/v1.3 http://www.ivoa.net/xml/VOTable/v1.3',
        }

    def save(self, jobname):
        """Save job description to VOTable file"""
        raw_jobname = jobname
        raw_jobname = raw_jobname.split('/')[-1]  # remove new/ prefix
        # VOTable root
        xmlns = self.xmlns_uris['xmlns']
        xsi = self.xmlns_uris['xmlns:xsi']
        jdl_tree = ETree.Element('VOTABLE', attrib={
            'version': '1.3',
            '{' + xsi + '}schemaLocation':
                'http://www.ivoa.net/xml/VOTable/v1.3 http://www.ivoa.net/xml/VOTable/v1.3',
        }, nsmap={'xsi': xsi, None: xmlns})
        resource = ETree.SubElement(jdl_tree, 'RESOURCE', attrib={
            'ID': raw_jobname,
            'name': raw_jobname,
            'type': "meta",
            'utype': "voprov:ActivityDescription"
        })
        # Job attributes
        if self.content['description']:
            ETree.SubElement(resource, 'DESCRIPTION').text = self.content['description'].decode()
        job_attr = [
            '<PARAM name="label" datatype="char" arraysize="*" value="{}" utype="voprov:ActivityDescription.label"/>'.format(self.content.get('label', raw_jobname)),
            '<PARAM name="type" datatype="char" arraysize="*" value="{}" utype="voprov:ActivityDescription.type"/>'.format(self.content.get('job_type', '')),
            '<PARAM name="subtype" datatype="char" arraysize="*" value="{}" utype="voprov:ActivityDescription.subtype"/>'.format(self.content.get('job_subtype', '')),
            '<PARAM name="version" datatype="float" value="{}" utype="voprov:ActivityDescription.version"/>'.format(self.content.get('version', '')),
            '<PARAM name="doculink" datatype="char" arraysize="*" value="{}" utype="voprov:ActivityDescription.doculink"/>'.format(self.content.get('doculink', '')),
            '<PARAM name="contact_name" datatype="char" arraysize="*" value="{}" utype="voprov:Agent.name"/>'.format(self.content.get('contact_name', '')),
            '<PARAM name="contact_email" datatype="char" arraysize="*" value="{}" utype="voprov:Agent.email"/>'.format(self.content.get('contact_email', '')),
            '<PARAM name="executionduration" datatype="int" value="{}" utype="uws:Job.executionduration"/>'.format(self.content.get('executionduration', '1')),
            '<PARAM name="quote" datatype="int" value="{}" utype="uws:Job.quote"/>'.format(self.content.get('quote', '1')),
        ]
        for attr in job_attr:
            resource.append(ETree.fromstring(attr))
        # Insert groups
        group_params = ETree.SubElement(resource, 'GROUP', attrib={
            'name': "InputParams",
            'utype': "voprov:Parameter",
        })
        group_used = ETree.SubElement(resource, 'GROUP', attrib={
            'name': "Used",
            'utype': "voprov:Used",
        })
        group_results = ETree.SubElement(resource, 'GROUP', attrib={
            'name': "Generated",
            'utype': "voprov:WasGeneratedBy",
        })
        # Prepare InputParams group
        for pname, p in self.content['parameters'].iteritems():
            param_attrib = {
                'ID': pname,
                'name': pname,
                'datatype': self.datatype_xs2vo[p['datatype']],
                'value': p['default'],
            }
            if param_attrib['datatype'] == 'char':
                param_attrib['arraysize'] = '*'
            if p['required']:
                param_attrib['type'] = 'no_query'
#                'required': str(p['required']),
#                'content_type': 'text/plain'
            param = ETree.Element('PARAM', attrib=param_attrib)
            ETree.SubElement(param, 'DESCRIPTION').text = p.get('description', '')
            if p.get('min', False) or p.get('max', False) or p.get('options', False):
                values = ETree.SubElement(param, 'VALUES')
                if p.get('min', False):
                    ETree.SubElement(values, 'MIN', attrib={'value': p['min']})
                if p.get('max', False):
                    ETree.SubElement(values, 'MAX', attrib={'value': p['max']})
                if p.get('options', False):
                    for o in p['options'].split(','):
                        ETree.SubElement(values, 'OPTION', attrib={'value': o})
            group_params.append(param)
        # Prepare used block
        for pname, p in self.content['used'].iteritems():
            attrib={
                'name': pname,
                'datatype': 'char',
                'arraysize': '*',
                'value': '',
                'xtype': p['content_type'],
                'utype': 'voprov:Entity',
            }
            if pname in self.content['parameters']:
                attrib['ref'] = pname
            used = ETree.Element('PARAM', attrib=attrib)
            #ETree.SubElement(used, 'DESCRIPTION').text = p.get('description', '')
            group_used.append(used)
        # Prepare results block
        for rname, r in self.content['results'].iteritems():
            attrib={
                'name': rname,
                'datatype': 'char',
                'arraysize': '*',
                'value': '',
                'xtype': r['content_type'],
                'utype': 'voprov:Entity',
            }
            if rname in self.content['parameters']:
                attrib['ref'] = rname
            result = ETree.Element('PARAM', attrib=attrib)
            #ETree.SubElement(result, 'DESCRIPTION').text = r.get('description', '')
            group_results.append(result)
        # Write file
        jdl_content = ETree.tostring(jdl_tree, pretty_print=True)
        jdl_fname = self._get_filename(jobname)
        with open(jdl_fname, 'w') as f:
            f.write(jdl_content)
            logger.info('JDL saved as VOTable: ' + jdl_fname)

    def read(self, jobname):
        """Read job description from VOTable file"""
        # TODO: all
        groups = {
            'InputParams': 'parameters',
            'Used': 'used',
            'Generated': 'results'
        }
        fname = self._get_filename(jobname)
        # '{}/{}{}'.format(JDL_PATH, job.jobname, self.extension)
        try:
            with open(fname, 'r') as f:
                jdl_string = f.read()
            print jdl_string
            jdl_tree = ETree.fromstring(jdl_string)
            print jdl_tree
            # Get default namespace
            xmlns = '{' + jdl_tree.nsmap[None] + '}'
            print xmlns
            # Read parameters description
            resource_block = jdl_tree.find(".//{}RESOURCE[@ID='{}']".format(xmlns, jobname))
            print resource_block
            job_def = {
                'name': resource_block.get('name'),
                'parameters': collections.OrderedDict(),
                'results': collections.OrderedDict(),
                'used': collections.OrderedDict()
            }
            for elt in resource_block.getchildren():

                if elt.tag == '{}DESCRIPTION'.format(xmlns):
                    job_def['description'] = elt.text
                    print elt.text
                if elt.tag == '{}PARAM'.format(xmlns):
                    # TODO: set datatype of value in the dictionary?
                    print elt.get('name'), elt.get('value')
                    job_def[elt.get('name')] = elt.get('value', '')
                if elt.tag == '{}GROUP'.format(xmlns):
                    group = groups[elt.get('name')]
                    print group
                    if group == 'parameters':
                        for p in elt:
                            if p.tag == '{}PARAM'.format(xmlns):
                                name = p.get('name')
                                print name, p.get('datatype', 'char')
                                item = {
                                    'datatype': self.datatype_vo2xs[p.get('datatype', 'char')],
                                    'required': p.get('type') != 'no_query',     # type="no_query" in VOTable
                                    'default': p.get('value'),
                                    'unit': p.get('unit', ''),
                                    'ucd': p.get('ucd', ''),
                                    'utype': p.get('utype', '')
                                }
                                for pp in p:
                                    if pp.tag == '{}DESCRIPTION'.format(xmlns):
                                        item['description'] = pp.text
                                    if pp.tag == '{}VALUES'.format(xmlns):
                                        options = []
                                        for ppp in pp:
                                            if ppp.tag == '{}MIN'.format(xmlns):
                                                item['min'] = ppp.get('value')
                                            if ppp.tag == '{}MAX'.format(xmlns):
                                                item['max'] = ppp.get('value')
                                            if ppp.tag == '{}OPTION'.format(xmlns):
                                                options.append(ppp.get('value'))
                                        item['options'] = ','.join(options)
                                job_def[group][name] = item
                    if group == 'used':
                        for p in elt:
                            name = p.get('name')
                            ref = p.get('ref')
                            item = {
                                'default': job_def['parameters'][ref]['default'],
                                'content_type': p.get('xtype'),
                                'description': job_def['parameters'][ref]['description']
                            }
                            job_def[group][name] = item
                    if group == 'results':
                        for p in elt:
                            name = p.get('name')
                            ref = p.get('ref')
                            item = {
                                'default': job_def['parameters'][ref]['default'],
                                'content_type': p.get('xtype'),
                                'description': job_def['parameters'][ref]['description']
                            }
                            job_def[group][name] = item
            # Log votable access
            # frame, filename, line_number, function_name, lines, index = inspect.stack()[1]
            # logger.debug('VOTable read at {} ({}:{}): {}'.format(function_name, filename, line_number, fname))
        except IOError:
            # if file does not exist, continue and return an empty dict
            logger.debug('VOTable not found for job {}'.format(jobname))
            raise UserWarning('VOTable not found for job {}'.format(jobname))
        except Exception as e:
            logger.error('{}'.format(e.message))
            raise
            # return {}
        self.content = job_def



class WADLFile(JDLFile):

    def __init__(self, jdl_path=JDL_PATH):
        self.extension = '.wadl'
        self.jdl_path = jdl_path
        self.xmlns_uris = {
            'xmlns:wadl': 'http://wadl.dev.java.net/2009/02',
            'xmlns:uws': 'http://www.ivoa.net/xml/UWS/v1.0',
            'xmlns:xlink': 'http://www.w3.org/1999/xlink',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:schemaLocation':
                'http://wadl.dev.java.net/2009/02 '
                'http://www.w3.org/Submission/wadl/wadl.xsd',
        }

    def save(self, jobname):
        """Save job description to WADL file"""
        raw_jobname = jobname
        raw_jobname = raw_jobname.split('/')[-1]  # remove new/ prefix
        # Prepare parameter blocks
        jdl_params = []
        jdl_popts = []
        for pname, p in self.content['parameters'].iteritems():
            # pline = '<param style="query" name="{}" type="{}" required="{}" default="{}"><doc>{}</doc></param>' \
            #        ''.format(pname, p['type'], p['required'], p['default'], p.get('description', ''))
            pelt_attrib = {
                'style': 'query',
                'name': pname,
                'type': p['datatype'],
                'required': str(p['required']),
                'default': p['default']
            }
            pelt = ETree.Element('param', attrib=pelt_attrib)
            ETree.SubElement(pelt, 'doc').text = p.get('description', '')
            jdl_params.append(pelt)
            # line = '<option value="{}" content_type="text/plain"><doc>{}</doc></option>' \
            #        ''.format(pname, p['description'])
            poelt = ETree.Element('option', attrib={
                'value': pname,
                'content_type': 'text/plain'
            })
            ETree.SubElement(poelt, 'doc').text = p.get('description', '')
            jdl_popts.append(poelt)
        # Prepare result block
        jdl_ropts = []
        for rname, r in self.content['results'].iteritems():
            # rline = '<option value="{}" content_type="{}" default="{}"><doc>{}</doc></option>' \
            #         ''.format(rname, r['content_type'], r['default'], r.get('description', ''))
            roelt = ETree.Element('option', attrib={
                'value': rname,
                'content_type': r['content_type'],
                'default': r['default']
            })
            ETree.SubElement(roelt, 'doc').text = r.get('description', '')
            jdl_ropts.append(roelt)
        # Read WADL UWS template as XML Tree
        filename = '{}/uws_template.wadl'.format(JDL_PATH)
        with open(filename, 'r') as f:
            jdl_string = f.read()
        jdl_tree = ETree.fromstring(jdl_string)
        xmlns = '{' + jdl_tree.nsmap[None] + '}'
        # Insert raw_jobname as the resource path
        joblist_block = jdl_tree.find(".//{}resource[@id='joblist']".format(xmlns))
        joblist_block.set('path', raw_jobname)
        joblist_block.set('url', self.content['url'])
        joblist_block.set('contact_name', self.content['contact_name'])
        joblist_block.set('contact_affil', self.content['contact_affil'])
        joblist_block.set('contact_email', self.content['contact_email'])
        # Insert job description
        job_list_description_block = jdl_tree.find(".//{}doc[@title='description']".format(xmlns))
        job_list_description_block.text = self.content['description'].decode()
        # Insert parameters
        params_block = {}
        for block in ['create_job_parameters', 'control_job_parameters', 'set_job_parameters']:
            params_block[block] = jdl_tree.find(".//{}request[@id='{}']".format(xmlns, block))
            for pelt in jdl_params:
                params_block[block].append(copy.copy(pelt))
        # Insert parameters as options
        param_opts_block = jdl_tree.find(".//{}param[@name='parameter-name']".format(xmlns))
        for poelt in jdl_popts:
            param_opts_block.append(poelt)
        # Insert results as options
        result_opts_block = jdl_tree.find(".//{}param[@name='result-id']".format(xmlns))
        for roelt in jdl_ropts:
            result_opts_block.append(roelt)
        # Insert default execution duration
        execdur_block = jdl_tree.find(".//{}param[@name='EXECUTIONDURATION']".format(xmlns))
        execdur_block.set('default', self.content['executionduration'])
        # Insert default quote
        quote_block = jdl_tree.find(".//{}representation[@id='quote']".format(xmlns))
        quote_block.set('default', self.content['quote'])
        jdl_content = ETree.tostring(jdl_tree, pretty_print=True)
        jdl_fname = self._get_filename(jobname)
        with open(jdl_fname, 'w') as f:
            f.write(jdl_content)
            logger.info('WADL saved: ' + jdl_fname)


    def read(self, jobname):
        """Read job description from WADL file"""
        fname = self._get_filename(jobname)
        # '{}/{}{}'.format(JDL_PATH, job.jobname, self.extension)
        parameters = collections.OrderedDict()
        results = collections.OrderedDict()
        used = collections.OrderedDict()
        try:
            with open(fname, 'r') as f:
                jdl_string = f.read()
            jdl_tree = ETree.fromstring(jdl_string)
            # Get default namespace
            xmlns = '{' + jdl_tree.nsmap[None] + '}'
            # Read parameters description
            params_block = jdl_tree.find(".//{}request[@id='create_job_parameters']".format(xmlns))
            for p in params_block.getchildren():
                pname = p.get('name')
                if pname not in ['PHASE', None]:
                    # TODO: Add all attributes (e.g. min, max for numbers)
                    parameters[pname] = {
                        'datatype': p.get('type'),
                        'required': p.get('required'),
                        'default': p.get('default'),
                        'description': list(p)[0].text,
                    }
                    for attr in ['min', 'max', 'choices']:
                        if p.get(attr):
                            parameters[pname][attr] = p.get(attr)
                    if p.get('type') in ['xs:anyURI', 'file']:
                        item = {
                            'default': parameters[pname]['default'],
                            'content_type': '',
                            'description': parameters[pname]['description']
                        }
                        used[pname] = item
            # Read results description
            results_block = jdl_tree.find(".//{}param[@name='result-id']".format(xmlns))
            for r in results_block.getchildren():
                if r.get('value') not in [None]:
                    ctype = r.get('content_type')
                    if not ctype:
                        ctype = r.get('mediaType')
                    results[r.get('value')] = {
                        'content_type': ctype,
                        'default': r.get('default'),
                        'description': list(r)[0].text,
                    }
            job_def = {
                'name': jobname,
                'parameters': parameters,
                'results': results,
                'used': used,
            }
            # Read job description
            joblist_description_block = jdl_tree.find(".//{}doc[@title='description']".format(xmlns))
            job_def['description'] = joblist_description_block.text
            # Read job attributes
            joblist_block = jdl_tree.find(".//{}resource[@id='joblist']".format(xmlns))
            job_def['url'] = joblist_block.get('url')
            job_def['contact_name'] = joblist_block.get('contact_name')
            job_def['contact_affil'] = joblist_block.get('contact_affil')
            job_def['contact_email'] = joblist_block.get('contact_email')
            # Read execution duration
            execdur_block = jdl_tree.find(".//{}param[@name='EXECUTIONDURATION']".format(xmlns))
            job_def['executionduration'] = execdur_block.get('default')
            # Read default quote
            quote_block = jdl_tree.find(".//{}representation[@id='quote']".format(xmlns))
            job_def['quote'] = quote_block.get('default')
            # Log wadl access
            frame, filename, line_number, function_name, lines, index = inspect.stack()[1]
            # logger.debug('WADL read at {} ({}:{}): {}'.format(function_name, filename, line_number, fname))
        except IOError:
            # if file does not exist, continue and return an empty dict
            logger.debug('WADL not found for job {}'.format(jobname))
            raise UserWarning('WADL not found for job {}'.format(jobname))
            # return {}
        self.content = job_def


# ---------
# Import PAR files (ftools, ctools)


def read_par(jobname):
    """
    Read .par file that contains the parameter list for a given tool
    The format of the file is from ftools/pfile, also used by ctools,
    it is an ASCII file with the following columns:
    name, type, parameter mode, default value, lower limit, upper limit, prompt
    See: http://heasarc.gsfc.nasa.gov/ftools/others/pfiles.html
    """
    type_dict = {
        'b': 'xs:boolean',
        'i': 'xs:long',
        'r': 'xs:double',
        's': 'xs:string',
        'f': 'xs:string'
    }
    filename = jobname+'.par'
    from astropy.io import ascii
    cnames = ['name', 'type', 'mode', 'default', 'lower', 'upper', 'prompt']
    data = ascii.read(filename, data_start=0, names=cnames)
    job_par = data
    for p in job_par:
        # Set if parameter is required (mode q and a)
        required = 'false'
        if ('q' in p['mode']) or ('a' in p['mode']):
            required = 'true'
        # If param is an integer or a real, add lower and upper limits (if not 0,0)
        lowup = ''
        if (('i' in p['type']) or ('r' in p['type'])) and (p['lower'] != '0' and p['upper'] != 0):
            lowup = ' lower="%s" upper="%s"' % (p['lower'], p['upper'])
        # If param is a string (but not 'mode'), does it have limited choices?
        choices = ''
        if ('s' in p['type']) and (p['lower'] != '') and (p['name'] != 'mode'):
            choices = ' choices="%s"' % (p['lower'])
        # Write param block to file
