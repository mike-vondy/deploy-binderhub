import time
from helpers import get_node, get_node_group, get_stdout

class ClusterDeployer:
    def __init__(self, cluster_conf, plugin_conf):
        # Deployer
        self.status = 'Initializing'

        # Cluster
        self.master_node = get_node(cluster_conf['nodes']['master'])
        self.worker_nodes = get_node_group(cluster_conf['nodes']['workers'])
        self.cluster_settings = cluster_conf['settings']

        # Plugins
        self.network_plugin = plugin_conf['network']
        self.service_plugin = plugin_conf['service']
        self.storage_plugin = plugin_conf['storage']

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.master_node.close()
        self.worker_nodes.close()

    def __str__(self):
        deployer_statements = []
        deployer_statements.append('--- Cluster Deployer ---')
        deployer_statements.append('Status: {}'.format(self.status))
        return '\n' + '\n'.join(deployer_statements) + '\n' #Just for simplifying the addition to prints

    def deploy(self):
        self.status = 'Cluster Deployment - Starting'
        self.cluster_initialize()
        self.install_network()
        self.status = 'Cluster Deployment - Complete'

    def cluster_initialize(self):
        self.status = 'Cluster Deployment - Running \'kubeadm init\''
        apiserver = self.cluster_settings['apiserver-advertise-address']
        pod_cidr = self.cluster_settings['pod-network-cidr']
        self.master_node.run('kubeadm init --apiserver-advertise-address={} --pod-network-cidr={}'.format(apiserver, pod_cidr), hide=True)
        
        self.status = 'Cluster Deployment - Making Kube Dir'
        self.master_node.run('mkdir -p $HOME/.kube')
        self.master_node.run('cp -i /etc/kubernetes/admin.conf $HOME/.kube/config')
        self.master_node.run('chown $(id -u):$(id -g) $HOME/.kube/config')

        self.status = 'Cluster Deployment - Joining Workers'
        join_command = get_stdout(self.master_node, 'kubeadm token create --print-join-command')
        self.worker_nodes.run(join_command)

        self.status = 'Cluster Deployment - Cluster Initialized'

    def install_helm(self):
        pass
    
    def install_network(self):
        pass

    def install_storage(self):
        pass

    def install_services(self):
        pass