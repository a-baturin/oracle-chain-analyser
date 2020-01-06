#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import getpass, cx_Oracle, re, json, os, glob, collections

#Predefined description blocks
patterns = [
    ('Merge into <b>{0[0]}</b><br>','merge(?:\s)+into(?:\s)+((\w+\.)*\w+)','DML'),
    ('Delete from <b>{0[0]}</b><br>','DELETE(?:\s)+FROM(?:\s)+((\w+\.)*\w+)','DML'),
    ('Insert into <b>{0[0]}</b><br>','INSERT(?:\s)+INTO(?:\s)+((\w+\.)*\w+)','DML'),
    ('Update <b>{0[0]}</b><br>','UPDATE(?:\s)+((\w+\.)*\w+)(?:\s)+(?:\w*)(?:\s)*SET','DML'),
    ('Update query<br>','UPDATE(?:\s)+\(','DML'),
    (
         'Call EXASOL script <b>{0[1]}.{0[0]}</b><br>',
         'Exasol_Call_Script\((?:\s)*(?:p_Script)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:p_Schema)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'',
         'EXASOL'
     ),
    (
         'Call EXASOL script <b>{0[0]}.{0[1]}</b><br>',
         'Exasol_Call_Script\((?:\s)*(?:p_Schema)+(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:p_Script)+(?:\s)*(?:=>)*(?:\s)*\'(.+)\'',
         'EXASOL'
    ),
    (
         'Import EXASOL table <b>{0[1]}.{0[0]}</b><br>',
         'Exasol_Import_Table\((?:\s)*(?:p_Table)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:p_Schema)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'',
         'EXASOL'
    ),
    (
         'Merge EXASOL table <b>{0[1]}.{0[0]}</b> from <b>{0[2]}</b> last <b>{0[3]}</b> days<br>',
         'Exasol_Merge_Table\((?:\s)*(?:p_Table)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:p_Target_Schema)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:p_Stage_Schema)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:p_Modified_Daysago)*(?:\s)*(?:=>)*(?:\s)*(\d+)',
         'EXASOL'
    ),
    (
         'Import EXASOL DI table <b>{0[1]}.{0[0]}</b><br>',
         'pkg_util_exasol_di\.do_export\((?:\s)*\'FULL\'(?:\s)*\,(?:\s)*(?:p_Table)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:p_Schema)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'',
         'EXASOL'
    ),
    (
         'Merge EXASOL DI table <b>{0[1]}.{0[0]}</b> from <b>{0[2]}</b> last <b>{0[3]}</b> days<br>',
         'pkg_util_exasol_di\.do_export\((?:\s)*\'MERGE\'(?:\s)*\,(?:\s)*(?:p_Table)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:p_Target_Schema)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:p_Stage_Schema)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:p_Modified_Daysago)*(?:\s)*(?:=>)*(?:\s)*(\d+)',
         'EXASOL'
    ),
    (
        'Call kettle <b>{0[2]}</b> <b>{0[1]}</b> from <b>{0[0]}</b><br>',
        'call_kettle_enterprise\((?:\s)*(?:directory)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:kettle_name)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'(?:\s)*,(?:\s)*(?:kettle_type)*(?:\s)*(?:=>)*(?:\s)*\'(.+)\'',
        'Kettle'),
    ('Execute <b>{0[0]}</b><br>','EXECUTE(?:\s)+IMMEDIATE(?:\s|\()+\'(.+)\'','')
]

groups = {
    'EXASOL':{'color':'green', 'short':'E'},
    'Kettle':{'color':'Coral', 'short':'K'},
    'DML':{'color':'inherit', 'short':''}
}

def process_proc(prc_text, start_pos, prev_pos, curr_o, curr_pk, curr_pr):
    if prc_text != '':
        curr_pos = start_pos
#remove comments of next proc
        prc_text = re.sub('(?<=;)(\s|--[^\n]*\n|(/\*((?!\*/).)*\*/))*$/s', '', prc_text, 1)
#remove comments
        comments = [x for t in re.findall('(--.*)|((?:\/\*){1}[\w\W]+?(?:\*\/){1})', prc_text) for x in t]
        prc_src = prc_text
        for comment in comments:
            if comment != '':
                prc_src = prc_src.replace(comment, '\n' * comment.count('\n'))

#split to commands
        prc_desc = ''
        prc_type = []
        prc_positions = []
        for command in prc_src.split(';'):
            for p in patterns:
                fnd = re.search(p[1], command, re.IGNORECASE)
                if fnd:
                    real_pos = curr_pos + command[:fnd.start()].count('\n')
                    prc_positions.append(real_pos)
                    prc_desc += f'<a href="#code-display.{real_pos}' + \
                                f'" style="color: blue">{real_pos:<5}' + \
                                p[0].format(fnd.groups()) + '</a>'
                    if p[2] not in prc_type and p[2] != '':
                        prc_type.append(p[2])
            curr_pos += command.count('\n')

        prc_text = '<pre id="code-display" class="line-numbers language-sql" ' + \
                    f'data-start="{start_pos}" ' + \
                    f'data-line-offset="{start_pos - 1}" ' + \
                    f'data-line="{",".join(map(str,prc_positions))}">' + \
                    f'<code class="language-sql">{prc_text}</code></pre>'
        return {curr_o + '.' + curr_pk + '.' + curr_pr:
            {
            'code': prc_text, 'start_pos': start_pos, 'end_pos': prev_pos,
            'owner': curr_o, 'package': curr_pk, 'proc': curr_pr,
            'description': prc_desc, 'type': prc_type
            }
        }
    else:
        return {}

def open_cursor(query_file):
    cursor = con.cursor()
    cursor.execute(open(query_file).read(),
        {'chain': connection['chain_name'], 'owner': connection['chain_owner']})
    cursor.rowfactory = collections.namedtuple("fields", [c[0] for c in cursor.description])
    return cursor

def write_file(result_filename, result_str):
    result_file = open(result_filename,"w+")
    result_file.write(result_str)
    result_file.close()

connection_filename = 'achain.connections.json'
connections =[]
connection = {}
connection_id = 0

if os.path.exists(connection_filename):
#Show connections menu
    connection_file = open(connection_filename)
    print(0, 'New connection')
    connections = json.loads(connection_file.read())
    connection_file.close()
    for rn, conn in enumerate(connections, 1):
        print (rn, conn['alias'])
    connection_id = int(input('Enter connection number: '))

if connection_id == 0:
    connection['database'] = input('TNS name: ')
    connection['login_name'] = input('Login name: ')
    connection['chain_owner'] = input('Chain owner: ')
    connection['chain_name'] = input('Chain name: ')
    connection['alias'] = input('Alias: ')
    connections.append(connection)
    print(json.dumps(connections, indent = 4))
    connection_file = open(connection_filename, 'w+')
    connection_file.write(json.dumps(connections))
    connection_file.close()
else:
    connection = connections[connection_id - 1]

con = cx_Oracle.connect(connection['login_name'], getpass.getpass('Enter password: '), connection['database'])

#Read source DDL
cur = open_cursor('proc_src.sql')

ddl_dict = {}
curr_o, curr_pk, curr_pr = '', '', ''
prc_text = ''
start_pos = -1
prev_pos = -1

for row in cur:
    if curr_o == row.OWNER and curr_pk == row.PACKAGE_NAME and curr_pr == row.PROCEDURE_NAME:
        prc_text += row.TEXT
        prev_pos = row.LINE
    else:
        ddl_dict = {**ddl_dict, **process_proc(prc_text, start_pos, prev_pos, curr_o, curr_pk, curr_pr)}
        prc_text = row.TEXT
        start_pos = row.LINE
        curr_o, curr_pk, curr_pr = row.OWNER, row.PACKAGE_NAME, row.PROCEDURE_NAME

ddl_dict = {**ddl_dict, **process_proc(prc_text, start_pos, prev_pos, curr_o, curr_pk, curr_pr)}

cur.close()

#Read chain
cur = open_cursor('chaincontents.sql')

chain_dict = {}
nodes = []
links = []
for row in cur:
    temp_step = {
        'chain_owner': row.CHAIN_OWNER,
        'chain': row.CHAIN,
        'step_name': row.STEP_NAME,
        'state': ' '.join(filter(bool,[row.SKIP, row.PAUSE, row.PAUSE_BEFORE])),
        'type': [],
        'comment': row.COMMENTS,
        'owner': row.OWNER,
        'package': row.PACKAGE,
        'procedure': '',
        'place': '',
        'code': '',
        'description': '',
        'condition': row.CONDITION,
        'step_type': row.STEP_TYPE
    }

    if row.STEP_TYPE == 'SUBCHAIN':
            temp_step['description'] = f'Subchain <b>{row.OWNER}.{row.PACKAGE}</b><br>'
    else:
        if row.IS_PKG == 0:
            temp_step['code'] = f'<pre id="code-display" class="line-numbers language-sql"><code class="language-sql">{row.PROCEDURE}</code></pre>'
        else:
            temp_step['procedure'] = row.PROCEDURE
            ddl_key = row.OWNER + '.' + row.PACKAGE + '.' + row.PROCEDURE
            if ddl_key in ddl_dict:
                temp_ddl = ddl_dict[ddl_key]
                temp_step['code'] = temp_ddl['code']
                temp_step['place'] = f'{temp_ddl["start_pos"]} - {temp_ddl["end_pos"]}'
                temp_step['description'] = temp_ddl['description']
                temp_step['type'] = temp_ddl['type']
            else:
                temp_step['code'] = 'ERROR Can''t find a procedure'

    temp_step['code'] = temp_step['code'].encode('ascii').hex()
    temp_step['description'] = temp_step['description'].encode('ascii').hex()

    step_name = row.CHAIN_OWNER + '.' + row.CHAIN + '.' + row.STEP_NAME
    chain_dict[step_name] = temp_step
    nodes.append({'name': step_name})
    if row.CONDITION != 'TRUE':
        links.extend(
            [{'source':row.CHAIN_OWNER + '.' + row.CHAIN + '.' + p[0],'target': step_name, 'type':p[1]} \
                 for p in [c.split(' ') for c in row.CONDITION.split(' AND ')]]
        )

write_file(
    f'chain.{connection["alias"]}.js',
    f'var obj = {json.dumps(chain_dict)};\n' + \
    f'var groups = {json.dumps(groups)};\n' + \
    f'var nodes = {json.dumps(nodes)};\n' + \
    f'var links = {json.dumps(links)};\n'
)

chains = ['.'.join(c.split('.')[1:-1]) for c in glob.glob("chain.*.js")]
chains.sort()

write_file('chain_names.js',
    f'var chains = {json.dumps(chains)};\nvar default_chain = "{connection["alias"]}"'
)

cur.close()
con.close()

