################ BIG OLD LOAD OF FUNCTIONS ################




######## Some imports etc

import networkx as nx

######## Some imports etc




######## Some functions to generate graphs from given nodes

# some functions that get you precessors, successors, or both. 
def predecessor_subnodes(graph, nodes) :
    
    '''
    for most cases you could just use the ancester function built in. 
    this lets you generalise to multiple nodes
    could probably also just repeatedly use the ancester function... 
    '''
    
    end_nodes = nodes.copy() 
    visited = set()
    while end_nodes:
        node = end_nodes.pop()
        visited.add(node)
        for parent in graph.predecessors(node):
            if parent in visited:
                continue
            end_nodes.append(parent)
    return visited ;

def successor_subnodes(graph, nodes) :
    
    '''
    for most cases you could just use the descendnts function built in. 
    this lets you generalise to multiple nodes
    could probably also just repeatedly use the descendnts function... 
    '''
    
    start_nodes = nodes.copy()
    visited = set()
    while start_nodes:
        node = start_nodes.pop()
        visited.add(node)
        for child in graph.successors(node):
            if child in visited:
                continue
            start_nodes.append(child)
    return visited ;

def subnodes(graph, nodes): 
    preds = predecessor_subnodes(graph, nodes)
    succs = successor_subnodes(graph, nodes)
    return preds.union(succs) ;  


# function that strips a grpah of unimportant nodes 
def cutdown_unimportant_nodes(graph, important_nodes) :
    
    iteration = 1
    while iteration == 1 or len(remove) != 0 : 

        potentially_remove = {node for node,degree in dict(graph.out_degree()).items() if degree == 0}
        remove = potentially_remove.difference(important_nodes)
        print(f"--- iteration number : {iteration}" ,end = " ")
        print(f"original size of graph : {len(list(graph.nodes))}" ,end = " ")
        print(f"terminus nodes : {len(potentially_remove)}" ,end = " ")
        print(f"unacceptable terminus nodes : {len(remove)}" ,end = " ")
        graph.remove_nodes_from(remove)
        print(f"new size of graph : {len(list(graph.nodes))}")
        iteration+=1
        
    return ; 
 

def collapse_nodes(graph) : 
    
    ##### this bit gets you a list of nodes to collapse

    # do a topo sort (this means once you find a candidate you can follow it to the end)
    # (...as you know you started at the beginning of a chain, not halfway through)
    # set up a to_check list (need it to be ordered so dont use a set)
    # loop through the list
    # check to see if it can be contracted 
    # move to the next node on the path
    to_check = list(nx.lexicographical_topological_sort(graph))
    collapse_lists = []
    while to_check:

        node_in_question = to_check[0]
        collapse_list = [node_in_question]
        should_i_check_more = True

        while should_i_check_more :  

            to_check.remove(node_in_question)
            should_i_check_more = False

            in_degree = graph.in_degree(node_in_question)
            out_degree = graph.out_degree(node_in_question)
            if in_degree == 1 and out_degree == 1: 

                # because the out_degree == 1 we know there is only one successor node
                successor_node = list(graph.successors(node_in_question))[0]
                suc_in_degree = graph.in_degree(successor_node)
                suc_out_degree = graph.out_degree(successor_node)
                if suc_in_degree == 1 and suc_out_degree != 0 : 

                    collapse_list.append(successor_node)
                    # move the node we're checking forward one postition
                    node_in_question = successor_node
                    should_i_check_more = True

        if len(collapse_list) > 1 : 
            collapse_lists.append(collapse_list)

    #### this bit actually cotracts the graph
    name_mapping = {}

    for collapse_list in collapse_lists : 

        map_to_node = collapse_list[0]
        new_name = map_to_node

        for node in collapse_list[1:] :
            # collapse the graph
            graph = nx.contracted_nodes(graph, map_to_node, node, self_loops = False)        
            # make a record of the new name
            new_name += "\n|"+node

        name_mapping[map_to_node] = new_name

    #### this bit actually relabels the graph
    # i have created a new object, tried not doing this and using <copy = False> but got ..
    # .. random "Freeze Graph" errors whereby couldnt make any more alterations. 
    new_graph = nx.relabel_nodes(graph, name_mapping, copy = True) 
    
    return new_graph; 

def explode_graph(graph, x_pos) :
    
    '''
    This function ADDS nodes. 
    If an edge path crosses more than one x_position a node is created. 
    This solves for edges overlapping each other.
    You need the x_positions of the nodes to know which edges would be longer than 1. 
    '''
    
    add_these_nodes = []
    add_these_edges = []
    remove_these_edges = []

    for node in graph :
        # print("\n {}, {}".format(node, x_pos[node]))

        for successor in graph.successors(node) : 
            # print(successor, x_pos[successor])
            node_index = 1
            nodes_to_add = x_pos[successor] - x_pos[node] - 1

            for i in range(0,nodes_to_add) :
                start_node = node + "->" + successor + "-" + str(i-1) 
                node_to_add = node + "->" + successor + "-" + str(i)
                if i == 0 : start_node = node
                add_these_edges.append((start_node, node_to_add))
                add_these_nodes.append(node_to_add)

            if nodes_to_add > 0 : 
                add_these_edges.append((node_to_add, successor))
                remove_these_edges.append((node,successor))    

    # add the edges (it just creates the nodes if they dont exist)  
    graph.add_edges_from(add_these_edges)
    # remove the edges 
    graph.remove_edges_from(remove_these_edges)
    # add a node attribute to show we have added it ourselves 
    add_these_nodes_dict = {}
    for node in graph :
        if node in add_these_nodes :
            add_these_nodes_dict[node] = 0
        else :
            add_these_nodes_dict[node] = 1
    nx.set_node_attributes(graph, add_these_nodes_dict, "is_real_node")
    
    return graph ; 


def predecessor_nodes(graph, node, important_nodes = []) :
    
    '''
    ### given a node in the graph: returns
    #### Predecessors
    * Direct preds (node ss_entitlements)
    * Important preds (node stripe_layer2, itunes_layer2, ...)
    * All preds (...) 
    * Final preds (node svod-prd-.entitlement) 
    '''
    
    direct_predecessors = set(graph.predecessors(node))
    all_predecessors = set(nx.ancestors(graph,node))
    terminal_predecessors = set()
    important_predecessors = set() 
    for pred in all_predecessors :
        if graph.in_degree(pred) == 0 : 
            terminal_predecessors.add(pred)
        if pred in important_nodes : 
            important_predecessors.add(pred)
        
    predecessors = {}
    predecessors['direct_predecessors'] = direct_predecessors
    predecessors['important_predecessors'] = important_predecessors
    predecessors['all_predecessors'] = all_predecessors
    predecessors['terminal_predecessors'] = terminal_predecessors
    
    return predecessors ; 
    
def successor_nodes(graph, node, important_nodes = []) :
    
    '''
    ### given a node in the graph: returns
    #### Successors
    * Direct succ `graph.successors(node)`
    * Important succ 
    * All succ `graph.descendants(node)`
    * Final succ
    '''
    
    direct_successors = set(graph.successors(node))
    all_successors = set(nx.descendants(graph,node))
    terminal_successors = set()
    important_successors = set() 
    for pred in all_successors :
        if graph.out_degree(pred) == 0 : 
            terminal_successors.add(pred)
        if pred in important_nodes : 
            important_successors.add(pred)
        
    successors = {}
    successors['direct_successors'] = direct_successors
    successors['important_successors'] = important_successors
    successors['all_successors'] = all_successors
    successors['terminal_successors'] = terminal_successors
    
    return successors ; 
 
######## Some functions to generate graphs from given nodes

    


######## Some functions to set the positions of the nodes 

def xpos_left_aligned(graph) : 
    
    # i will need the longest path length (defines the width of the graph!)
    longest_path = len(nx.dag_longest_path(graph))

    # i dont know why but you can only use the sort one time when its defined.. so saving it to a list for ease
    topo_order = list(nx.topological_sort(graph))

    # run through the nodes
    # (start nodes) nodes with no predecessors : 0
    # (terminus nodes) essentially reports : longest_path
    # all others : 
    # - search the predecessors (this is possible because the sort if a topo sort!) 
    # - take the position so far from the predecessors
    x_pos = dict(graph.nodes)
    for i in topo_order:
        x_pos[i] = 0    
        if graph.in_degree(i) == 0 : 
            pass 
        elif graph.out_degree(i) == 0 : 
            x_pos[i] = longest_path - 1
        else :
            max_value_from_predecessor = 0
            for j in graph.predecessors(i):
                max_value_from_predecessor = max(max_value_from_predecessor,x_pos[j])
            x_pos[i] = max_value_from_predecessor + 1

    return x_pos ; 
      
def ypos_simple_distributed(graph, x_pos): 
    
    # will need to iterate over the x positions
    distinct_x_values = list(set(x_pos.values()))
    distinct_x_values.sort()
    
    # set the y position
    # assign any old order for now, so long as not overlapping. 
    # consider in the future some enhancements here
    y_pos = dict(graph.nodes)
    for i in distinct_x_values : 
        iterator = 0
        for key, value in x_pos.items(): 
            if value == i : 
                y_pos[key] = iterator 
                iterator += 1
        # redistributes the y coords
        # feels clunky to loop through again
        for key, value in x_pos.items(): 
            if value == i : 
                y_pos[key] = y_pos[key] / iterator
    
    return y_pos ; 

def get_nodes_in_xpos(x_pos, position) : 
    keys = []
    for key, value in x_pos.items(): 
        if value == position :
            keys.append(key)
    keys.sort() 
    return keys ;    

def ypos_(graph, x_pos): 
    
    '''
    run through first layer of nodes. distribute
    take the next layer of nodes. if any have in_degree = 1, and the out_degree = 1 then inherit the same postition. 
    alt: take the average postition
    ''' 
    
    
    # will need to iterate over the x positions
    distinct_x_values = list(set(x_pos.values()))
    distinct_x_values.sort()  
  
    # initialise a dict to hold the positional values
    y_pos = dict(graph.nodes)
    
    # loop through the x coords (1,2,3,4,...)
    for i in distinct_x_values :
        
        temp_dict = {}
        
        # loop through the nodes in a specific x coord (node4, node9, node13, node44,...)
        for j in get_nodes_in_xpos(x_pos,i) :
            
            # grab the predecessors loop through them (node1, node2, node3, node5,...)
            the_count = 0 
            the_sum = 0 
            predecessors = graph.predecessors(j)
            for predecessor in predecessors : 
                the_count += 1
                the_sum += y_pos[predecessor]
            try: 
                the_average = the_sum / the_count
            # stick nodes with no preds at the bottom of the graph
            # could use 1 to stick them at the top
            except ZeroDivisionError: 
                the_average = 0

            temp_dict[j] = the_average
    
        # redistribute (as you might have clashes) 
        sorted_temp_dict = {}
        sorted_temp_list = sorted(temp_dict.items(), key=lambda x: x[1] ) # jobo gave me this line - thanks! 

        for k in range(len(sorted_temp_list)) :
            key = sorted_temp_list[k][0]
            value = sorted_temp_list[k][1]
            try :
                sorted_temp_dict[key] = k / (len(sorted_temp_list) - 1) # edit this line to be a square graph
            except ZeroDivisionError :
                sorted_temp_dict[key] = 0.5
                
        # update the dictionary 
        y_pos.update(sorted_temp_dict)
        
    return y_pos ;

######## Some functions to set the positions of the nodes 




######## Some functions to colour the graph with attributes

def node_type(graph, colourings, inplace = True):
    
    # holder for the colours
    node_colouring = dict(graph.nodes)
    
    # go through the nodes
    for node in node_colouring :
        
        # set basic colours
        if graph.in_degree(node) == 0 :
            node_colouring[node] = 1
        elif graph.out_degree(node) == 0 :
            node_colouring[node] = 2
        else :
            node_colouring[node] = 0
            
        # run through the colourings, set more colours
        for colouring in colourings :
            if node in colouring : 
                node_colouring[node] = -(colourings.index(colouring) + 1)
                break # break out of the loop, stop checking
    
    if inplace:      
        return nx.set_node_attributes(graph, node_colouring, "node_colouring")  ; 
    else : 
        return node_colouring ; 
   
    
def set_node_text(graph, shortmessage = True, inplace = True): 
    
    '''
    A simple function to set the node text for a node. 
    Sets the attributes of the graph in place with Node name and predecessors
    '''
    
    # holder for the colours
    node_texts = dict(graph.nodes)
    
    # go through the nodes
    for node in node_texts: 
    
        # gather some infomation about the nodes
        preds = predecessor_nodes(graph,node)
        succs = successor_nodes(graph,node)

        # write some text
        text_for_node = f'Node: <b>{node}</b>'
        
        # Direct predecessors and all predecessors
        text_for_node += '<br>'
        text_for_node += f"Direct Predecessors: {len(preds['direct_predecessors'])}"
        text_for_node += '<br>'
        text_for_node += f"All Predecessors: {len(preds['all_predecessors'])}"
        # Terminal predecessors
        text_for_node += '<br>'
        text_for_node += 'Terminal Predecessors:'
        if shortmessage : 
            text_for_node += f" {len(preds['terminal_predecessors'])}"
        elif len(preds['terminal_predecessors']) > 0 : 
            text_for_node += '<br> - '
            text_for_node += '<br> - '.join(p for p in preds['terminal_predecessors'])
        else : 
            text_for_node += ' None' 
        
        # Successor bits
        text_for_node += '<br>'
        text_for_node += f"Direct Successors: {len(succs['direct_successors'])}"
        text_for_node += '<br>'
        text_for_node += f"All Successors: {len(succs['all_successors'])}"
        # Terminal predecessors
        text_for_node += '<br>'
        text_for_node += 'Terminal Successors:'
        if shortmessage : 
            text_for_node += f" {len(succs['terminal_successors'])}"
        elif len(succs['terminal_successors']) > 0 : 
            text_for_node += '<br> - '
            text_for_node += '<br> - '.join(p for p in succs['terminal_successors'])
        else : 
            text_for_node += ' None' 
            
        # update the dict
        node_texts[node] = text_for_node

    if inplace: 
        return nx.set_node_attributes(graph, node_texts, "node_text") ; 
    else: 
        return node_texts ; 