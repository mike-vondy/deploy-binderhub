from helpers import get_node_group, install_apt_packages, group_put, single_put, get_stdout
import time

'''
ClusterPreparer: Class the prepares each node in the cluster for kubernetes initialization.
Details:
1. Collects nodes in cluster from /config/cluster/nodes.yaml
2. Initializes a Fabric ThreadingGroup with each of the nodes.
3. Installs standard apt-packages
4. Installs Docker (Need to maintain for compatible versions)
5. Installs KubeADM (Need to maintain for comptible versions)
(Also Moves specific files into the right places on hosts as well as various other commands)
'''

RESOURCE_DIR = '/resources/cluster'

class ClusterPreparer:
    def __init__(self, cluster_conf):
        self.status = 'Initializing'
        self.cluster_nodes = get_node_group([cluster_conf['nodes']['master']] + cluster_conf['nodes']['workers'])
        self.base_packages = cluster_conf['packages']
        self.docker_packages = cluster_conf['docker']
        self.kube_packages = cluster_conf['kubernetes']

    def __enter__(self):
        self.status = 'Entering'
        return self

    def __exit__(self, *args):
        print('Closing Cluster Preperation - Exit Status: {}'.format(self.status))
        self.cluster_nodes.close() 

    def __str__(self):
        preparer_statements = []
        preparer_statements.append('--- Cluster Preparer ---')
        preparer_statements.append('Nodes: {}'.format(len(self.cluster_nodes)))
        preparer_statements.append('Status: {}'.format(self.status))
        return '\n' + '\n'.join(preparer_statements) + '\n' #Just for simplifying the addition to prints

    def prepare(self):
        self.status = 'Started'
        
        self.base_preperation()
        self.install_docker()
        self.install_kubernetes()

        self.status = 'Complete'

    def base_preperation(self):
        self.status = 'Base Preperation - Started'
        self.status = 'Base Preperation - Node Configuration'
        self.cluster_nodes.run('swapoff -a; sed -i \'/swap/d\' /etc/fstab')
        group_put(self.cluster_nodes, '{}/k8s.conf'.format(RESOURCE_DIR), '/etc/sysctl.d/k8s.conf')
        self.cluster_nodes.run('sysctl --system')
        
        self.status = 'Base Preperation - Installing Base Packages'
        install_apt_packages(self.cluster_nodes, self.base_packages)
        
        self.status = 'Base Preperation - Complete'

    def install_docker(self):
        self.status = 'Docker Installation - Started'
        self.cluster_nodes.run('curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -', hide=True)
        self.cluster_nodes.run('sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"')
        
        self.status = 'Docker Installation - Installing Packages'
        install_apt_packages(self.cluster_nodes, self.docker_packages, hold=True)

        self.status = 'Docker Installation - Configuration'
        group_put(self.cluster_nodes, '{}/daemon.json'.format(RESOURCE_DIR), '/etc/docker/daemon.json')
        self.cluster_nodes.run('mkdir -p /etc/systemd/system/docker.service.d')
        self.cluster_nodes.run('systemctl daemon-reload')
        self.cluster_nodes.run('systemctl restart docker')
        self.cluster_nodes.run('systemctl enable docker')
        
        self.status = 'Docker Installation - Complete'

    def install_kubernetes(self):
        self.status = 'Kubernetes Installation - Started'
        self.cluster_nodes.run('curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -', hide=True)
        group_put(self.cluster_nodes, '{}/kubernetes.list'.format(RESOURCE_DIR), '/etc/apt/sources.list.d/kubernetes.list')

        self.status = 'Kubernetes Installation - Installing Packages'
        install_apt_packages(self.cluster_nodes, self.kube_packages, hold=True)

        self.status = 'Kubernetes Installation - Complete'