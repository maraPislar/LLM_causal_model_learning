import sys, os
sys.path.append(os.path.join('..', '..'))

import argparse
from pyvene import set_seed
import torch
import numpy as np
from causal_models import ArithmeticCausalModels
import matplotlib.pyplot as plt
import networkx as nx
import itertools

def get_all_combinations(cliques):
    all_combinations = list(itertools.product(*cliques.values()))
    return all_combinations

def filter_by_max_length(list_of_lists):
    max_len = max(len(sublist) for sublist in list_of_lists)
    return [sublist for sublist in list_of_lists if len(sublist) == max_len]

def calculate_overlap(tuple_):
    total_count = 0
    overlapping_percentage = 0
    merged_set = set()
    for sublist in tuple_:
        total_count += len(sublist)
        merged_set = merged_set.union(set(sublist)) # merge sets
    overlap = total_count - len(merged_set)
    if total_count != 0:
        overlapping_percentage = (overlap / total_count)
    return overlapping_percentage, overlap

def find_least_overlap_tuple(list_of_tuples):
    min_overlap = float('inf')
    best_tuple = None

    for tuple_ in list_of_tuples:
        _, overlap = calculate_overlap(tuple_)
        if overlap < min_overlap:
            min_overlap = overlap
            best_tuple = tuple_

    return best_tuple

def generate_random_graph(size=1000):
    graph = torch.zeros((size, size))

    for i in range(size):
        for j in range(i + 1, size):
            graph[i, j] = torch.randint(1, 4, (1,))

    graph += graph.t().clone()
    return graph

def main():
    
    parser = argparse.ArgumentParser(description="Process experiment parameters.")
    # parser.add_argument('--model_path', type=str, help='path to the finetuned GPT2ForSequenceClassification on the arithmetic task')
    parser.add_argument('--results_path', type=str, default='disentangling_results/', help='path to the results folder')
    parser.add_argument('--seed', type=int, default=43, help='experiment seed to be able to reproduce the results')
    args = parser.parse_args()

    # if not os.path.exists(args.model_path):
    #     raise argparse.ArgumentTypeError("Invalid model_path. Path does not exist.")
    
    if not os.path.exists(args.results_path):
        raise argparse.ArgumentTypeError("Invalid results_path. Path does not exist.")

    # load labelled graph
    graph_path = os.path.join(args.results_path, 'arithmetic/graphs/graph_0.pt')
    graph = torch.load(graph_path)
    
    set_seed(args.seed)
    
    arithmetic_family = ArithmeticCausalModels()

    # construct entire graph
    G = nx.Graph()

    print('constructing entire graph')

    for i in range(graph.shape[0]):
        G.add_node(i)

    # undirected graph edge-label construction
    for i in range(graph.shape[0]):
        for j in range(i+1, graph.shape[0]):
            if graph[i, j] != 0:
                G.add_edge(i, j, label=graph[i, j].item()) # label means the causal model

    # construct subgraphs based on label
    print('Constructing subgraphs')
    subgraphs = {}
    n_nodes = {}
    for label in set(nx.get_edge_attributes(G, 'label').values()):
        subgraph = nx.Graph()

        for u, v, data in G.edges(data=True):
            if data['label'] == label:

                if u not in subgraph.nodes(): 
                    subgraph.add_node(u)
                if v not in subgraph.nodes():
                    subgraph.add_node(v)

                if not subgraph.has_edge(u, v):
                    subgraph.add_edge(u, v, label=label)
        n_nodes[label] = subgraph.number_of_nodes()
        subgraphs[arithmetic_family.get_label_by_id(label)] = subgraph

    # find optimal positions for each subgraph
    positions = {}
    for label, subgraph in subgraphs.items():
        # spring layout is an algorithm for showing the graph in a pretty way
        positions[label] = nx.spring_layout(subgraph, k=0.3, iterations=50)

    num_subgraphs = len(subgraphs.keys())
    fig, axes = plt.subplots(nrows=1, ncols=num_subgraphs, figsize=(12, 5))

    color_map = {1: 'red', 2: 'green', 3: 'blue'}

    i = 0 # axes id
    maximal_cliques = {}
    print('finding cliques')
    for label, subgraph in subgraphs.items():
        
        print(f'finding cliques for graph {label}')
        cliques = list(nx.find_cliques(subgraph))
        maximal_cliques[label] = filter_by_max_length(cliques)
        print(maximal_cliques[label])
        pos = positions[label]

        # visualizing the subgraphs
        nx.draw_networkx(
            subgraph, 
            pos=pos, 
            node_size=40, 
            node_color='lightblue', 
            edge_color=[color_map[subgraph[u][v]['label']] for u, v in subgraph.edges()],
            with_labels=True, 
            font_size=8,
            ax=axes[i]
        )

        axes[i].axis('off')
        axes[i].set_title(f"All connected edges with label {label}")
        i += 1

    plt.tight_layout()
    plt.savefig('connected_component_visualization.png')
    plt.close()

    print(n_nodes)

    print('getting the best combo')
    print(maximal_cliques)
    all_combinations = get_all_combinations(maximal_cliques)
    best_combo = find_least_overlap_tuple(all_combinations) # getting disjoint lists of cliques
    overlap_percentage, _ = calculate_overlap(best_combo)
    print(f'Percentage of how disjoint are the cliques from each subgraph: {overlap_percentage}')
    i = 0
    for data in best_combo:
        print(data)
        print(f'Percentage out of the entire subgraph for causal model {i+1} data: {len(data)/n_nodes[i+1]}')
        best_combo_path = os.path.join(args.results_path, f'class_data_{i+1}.npy')
        np.save(best_combo_path, data)
        # loaded_arr = np.load(best_combo_path, allow_pickle=True)
        i += 1
    
if __name__ =="__main__":
    main()