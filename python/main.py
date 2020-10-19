from helpers import get_node, get_node_group, read_conf
from ClusterPreparer import ClusterPreparer
from threading import Thread
import time
#from MasterNode import MasterNode
#from WorkerNode import WorkerNode

if __name__=="__main__":
    print('### Preparing Kubernetes Cluster Nodes ###')
    cluster_conf = read_conf('config/cluster/nodes.yaml')
    with ClusterPreparer(cluster_conf) as cluster:
        status_watcher = Thread(target=cluster.prepare)
        status_watcher.start()
        current_status = cluster.status
        while True:
            if current_status != cluster.status:
                print(cluster)
            current_status = cluster.status
            if current_status == 'Complete' or current_status == 'Exiting':
                print('--- Cluster Preperation Complete ---')
                break
            
    #""" Deploy Kube Here
    #"""
    #master_node = get_node(node_conf["master"])
    #worker_nodes = get_node_group(node_conf["workers"])
#
    #master_node.run("echo - Master Node Reached")
    #worker_nodes.run("echo - Worker Node Reached")
#
    #plugin_conf = read_conf('config/cluster/plugins.yaml')
    ##print(node_conf, plugin_conf)  
