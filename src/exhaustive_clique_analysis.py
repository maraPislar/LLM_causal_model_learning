import sys, os
sys.path.append(os.path.join('..', '..'))

import argparse
from pyvene import set_seed
import torch
import numpy as np
from causal_models import ArithmeticCausalModels, SimpleSummingCausalModels
import matplotlib.pyplot as plt
import networkx as nx
from itertools import product
from utils import filter_by_max_length
import pickle
import json
from networkx.readwrite import json_graph

def main():
    
    parser = argparse.ArgumentParser(description="Process experiment parameters.")
    parser.add_argument('--results_path', type=str, default='disentangling_results/', help='path to the results folder where you have saved the graphs')
    parser.add_argument('--causal_model_type', type=str, choices=['arithmetic', 'simple'], default='arithmetic', help='choose between arithmetic or simple')
    parser.add_argument('--layer', type=int, default=0, help='layer corresponding to the graphs obtained that you want to analyse')
    parser.add_argument('--low_rank_dimension', type=int, default=256, help='low_rank_dimension corresponding to the graphs obtained that you want to analyse')
    parser.add_argument('--seed', type=int, default=43, help='experiment seed to be able to reproduce the results')
    args = parser.parse_args()

    if args.causal_model_type == 'arithmetic':
        arithmetic_family = ArithmeticCausalModels()
    elif args.causal_model_type == 'simple':
        arithmetic_family = SimpleSummingCausalModels()
    else:
        raise ValueError(f"Invalid causal model type: {args.causal_model_type}. Can only choose between arithmetic or simple.")

    args.results_path = os.path.join(args.results_path, args.causal_model_type)
    if not os.path.exists(args.results_path):
        raise argparse.ArgumentTypeError("Invalid results_path. Path does not exist.")
    
    classification_path = os.path.join(args.results_path, 'classification_data')
    os.makedirs(classification_path, exist_ok=True)

    cliques_info_path = os.path.join(args.results_path, 'cliques_info')
    os.makedirs(cliques_info_path, exist_ok=True)
    
    set_seed(args.seed)

    maximal_cliques = {}

    _, axes = plt.subplots(1, 3, figsize=(15, 5))
    # colors = ["skyblue", "lightcoral", "lightgreen"]

    # i = 0

    cliques_info = {}

    for cm_id, model_info in arithmetic_family.causal_models.items():

        cliques_info[cm_id] = {}

        print(f'Loading graph {cm_id}..')
        graph_path = os.path.join(args.results_path, f'graphs/cm_{cm_id}/graph_{args.low_rank_dimension}_{args.layer}.pt')
        graph = torch.load(graph_path)
        mask = (graph == 1).float()
        graph = graph * mask
        graph.fill_diagonal_(0)

        print('Constructing graph..')
        G = nx.from_numpy_array(graph.numpy())

        print('Finding cliques..')
        cliques = list(nx.find_cliques(G))
        maximal_cliques[cm_id] = filter_by_max_length(cliques)
        
        max_clique_nodes = set(node for clique in maximal_cliques[cm_id] for node in clique)

        # percentage of edges ?
        G_subgraph = G.subgraph(max_clique_nodes)
        percentage_of_edges = G_subgraph.number_of_edges() / G.number_of_edges()

        cliques_info[cm_id]['number_of_max_len_cliques'] = len(maximal_cliques[cm_id])
        cliques_info[cm_id]['clique_size'] = len(maximal_cliques[cm_id][0])
        cliques_info[cm_id]['number_of_unique_nodes_in_all_cliques'] = len(max_clique_nodes)
        cliques_info[cm_id]['nodes_percentage'] = len(max_clique_nodes) / len(graph)
        cliques_info[cm_id]['edge_percentage'] = percentage_of_edges
        cliques_info[cm_id]['cliques_subgraph'] = json_graph.node_link_data(G_subgraph)

        # save the ids of the nodes to use in the classification part
        nodes_list = list(max_clique_nodes)
        save_data_path = os.path.join(classification_path, f'{args.low_rank_dimension}')
        os.makedirs(save_data_path, exist_ok=True)
        data_path = os.path.join(save_data_path, f'data_{cm_id}_{args.layer}.pkl')
        
        with open(data_path, 'wb') as f:
            pickle.dump(nodes_list, f)

        # get a set of all common nodes between cliques
        # nodes_in_all_max_cliques = set.intersection(*map(set, maximal_cliques[cm_id]))
        # print("Nodes in all maximal cliques:", nodes_in_all_max_cliques)

        # print("Creating subgraph for maximal cliques")
        # G_nx = G_subgraph.copy()
        # pos_nx = nx.spring_layout(G_nx, seed=args.seed)
        # nx.draw(G_nx, pos=pos_nx, with_labels=True, font_size=8, ax=axes[i])
        # axes[i].set_title(model_info['label'])

        # i += 1

    # plt.savefig('graphs.png')
    # plt.close()

    temp_path = os.path.join(cliques_info_path, f'{args.low_rank_dimension}')
    os.makedirs(temp_path, exist_ok=True)
    temp_path = os.path.join(temp_path, f'layer_{args.layer}.json')
        
    with open(temp_path, 'w') as file:
        json.dump(cliques_info, file)

    # loading back the graph of maximal cliques
    # with open(temp_path, 'r') as file:
    #     cliques_info = json.load(file)
        
    # subgraph_data = cliques_info[cm_id]['cliques_subgraph']
    # G_subgraph = json_graph.node_link_graph(subgraph_data)

if __name__ =="__main__":
    main()