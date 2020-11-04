# Defines Helpers for classes to import

import yaml
from fabric import Connection, ThreadingGroup 


# Working with Conf Files
def read_conf(conf_file):
    with open(conf_file) as f:
        yaml_data = yaml.load(f, Loader=yaml.FullLoader)
    return yaml_data

def write_conf(conf_file, data):
    with open(conf_file, 'w') as f:
        yaml.dump(data, f)

# Working with Fabric
def group_put(conn_group, local_path, remote_path):
    for conn in conn_group:
        conn.put(local_path, remote=remote_path)

def single_put(conn, local_path, remote_path):
    conn.put(local_path, remote=remote_path)

def get_stdout(conn, command):
    stdout = conn.run(command, hide=True).stdout
    return stdout

def install_apt_packages(conn_group, package_list, hold=False):
    conn_group.run('apt-get update', hide=True)
    conn_group.run('apt-get install -y {}'.format(' '.join(package_list)), hide=True)
    if hold:
        conn_group.run('apt-mark hold {}'.format(' '.join(package_list)), hide=True)

def get_node(node):
    return Connection(node)

def get_node_group(node_list):
    return ThreadingGroup(*node_list, forward_agent=True)