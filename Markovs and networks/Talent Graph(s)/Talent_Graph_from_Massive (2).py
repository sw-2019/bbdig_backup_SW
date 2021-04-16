bb_palette={'Sunset Red':'#D2525D', 'Dorset Blue':'#4BA0B8','Union Blue':'#083560','Sunset Red Highlight':'#FF8F99',\
           'Dorset Blue Highlight':'#5CCAE5','Union Blue Highlight':'#80E4FF','Raspberry':'#993F64'\
            ,'Orange':'#E0835E','Apricot':'#E8B35D','Apple':'#72B58C','Dark Storm':'#1E2023','Mild Storm':'#282B31'\
           ,'Light Storm':'#3E434B','Dark Cloud':'#CDD2D8','Light Cloud':'#E8EDF2','White':'#FFFFFF'}

import networkx as nx
import pandas as pd
import sqlite3
import itertools
import matplotlib.pyplot as plt
import numpy as np

def Refresh_Talent_Graph():

    pd.set_option('display.max_colwidth', -1)

    catalog_df=pd.read_csv(r"http://itv-catalog.massive-itv.com/catalog.csv")
    conn = sqlite3.connect('SQL_connection1.db') #Create a connection object

    # Put the pandas table into the connection object
    try:
        try:
            query=conn.cursor()
            query.execute('''drop table Catalogue_info''')
            query.fetchall()
            query.close()
        except:
            pass
        catalog_df.to_sql('Catalogue_info',con=conn)
    except:
        pass

    query=conn.cursor()

    try:
        query.execute('''drop table eps''')
    except:
        pass

    query.execute("""create table eps as 
    select 
    ParentId
    ,Id as EpisodeID
    ,EpisodeNumber
    ,MetaDuration 
    ,MediaDuration
    , ItemType
     ,CustomId
     ,MetaCreditsCast
     ,MetaCreditsCrew
    from Catalogue_info
    where ItemType='episode' """)

    try:
        query.execute('''drop table seasons''')
    except:
        pass

    query.execute("""create table seasons as 
    select ParentId
    ,ID
    ,Title as Series_number_text
    ,SeasonNumber as Series_number
    ,ItemType
    , CustomId
     ,MetaCreditsCast
     ,MetaCreditsCrew
    from Catalogue_info
    where ItemType='season' """)

    try:
        query.execute('''drop table shows''')
    except:
        pass

    query.execute("""
    create table shows as 
    select Title as programme_name
    ,Id as Programme_ID
    ,ItemType as Programme_Type
    ,null as Series_number_text
    ,null as Series_number
    ,null as Series_ID
    ,null as Episode_ID
    ,null as Episode_Number
    ,null as Meta_Duration 
    ,null as Media_Duration
    ,Id
    ,CustomId
    , MetaCreditsCast
     ,MetaCreditsCrew
    from Catalogue_info
    where ItemType not in ('season','episode') 
    """)


    try:
        query.execute('''drop table seasons2''')
    except:
        pass

    query.execute("""create table seasons2 as
    select shows.programme_name
    ,shows.Programme_ID
    ,seasons.ItemType as Programme_Type
    ,seasons.Series_number_text
    ,seasons.Series_number
    ,seasons.Id as Series_ID
    ,null as Episode_ID
    ,null as Episode_Number
    ,null as Meta_Duration 
    ,null as Media_Duration
    ,seasons.ID
    ,seasons.CustomId 
    ,seasons.MetaCreditsCast
     ,seasons.MetaCreditsCrew
    from seasons
    left join shows
     on seasons.parentid=shows.id
     """)

    try:
        query.execute('''drop table episodes2''')
    except:
        pass

    query.execute("""create table episodes2 as
    select
    seas.programme_name
    ,seas.Programme_ID
    ,eps.ItemType as Programme_Type
    ,seas.Series_number_text
    ,seas.Series_number
    ,seas.Series_ID
    ,eps.EpisodeID as Episode_ID
    ,eps.EpisodeNumber as Episode_Number
    ,eps.MetaDuration as Meta_Duration 
    ,eps.MediaDuration as Media_Duration
    ,eps.EpisodeID as ID
    ,eps.CustomId 
    ,eps.MetaCreditsCast
    ,eps.MetaCreditsCrew
     from eps
     left join
     seasons2 seas
     on eps.parentId=seas.id""")



    try:
        query.execute('''drop table catalogue_cleaned''')
    except:
        pass

    query.execute("""create table catalogue_cleaned as
    select * from shows
    union all
    select * from seasons2
    union all 
    select * from episodes2
    """)

    query.fetchall()
    query.close()


    tidy_table=pd.read_sql_query("""select * from catalogue_cleaned""", conn)
    show_list_of_dicts=tidy_table.to_dict(orient='records')
    talent_nodes=[]
    show_nodes=[]
    edges=[]

    import re
    for n,i in enumerate(show_list_of_dicts):
        if i['Programme_Type'] not in ['show','season']:
            if i['MetaCreditsCast'] and len(i['MetaCreditsCast'])>0:
                show_name=i['programme_name'].strip()
                
                show_nodes.append(show_name)
                cast_list=re.split(',',i['MetaCreditsCast'])
                for j in cast_list:
                    talent_name=re.split(' as ',j)[0].strip()
                   
                    talent_nodes.append(talent_name)
                    edges.append((talent_name,show_name))
    talent_map_df = pd.DataFrame(edges,columns=['Talent','Show'])
    conn = sqlite3.connect('SQL_connection1.db') #Create a connection object

    # Put the pandas table into the connection object
    query=conn.cursor()
    try:
        query.execute('''drop table talent_map''')
    except:
        pass
    talent_map_df.to_sql('talent_map',con=conn)

    query.fetchall()
    query.close()


    talent_edges=pd.read_sql_query("""
    select a.show, a.talent,
    cast(a.n_eps as real)/b.total_num_eps as Pc_episodes
    from
        (select 
        show, talent, count(*) as N_eps
        from talent_map
        group by 1,2) a
    inner join
        (select programme_name as show, 
        count(*) as total_num_eps
        from catalogue_cleaned 
        where Programme_Type not in ('show','season')
        group by 1) b
    on a.show=b.show
    """, conn)
    edges = [tuple(x) for x in talent_edges.values]
    import networkx as nx
    import matplotlib.pyplot as plt
    talent_nodes=list(set(talent_nodes))
    show_nodes=list(set(show_nodes))
    G=nx.Graph()
    G.add_nodes_from(talent_nodes, bipartite='talent')
    G.add_nodes_from(show_nodes, bipartite='show')
    G.add_weighted_edges_from(edges)
    
    return G,talent_nodes, show_nodes,edges

def Show_all_shows_for_cast(all_graph,cast_name):
    G=all_graph[0]
    if cast_name in G.nodes():
        # Returns all the shows which someone has been in
        actor_shows=[]
        for i in nx.all_neighbors(G,cast_name):
            print(i)
            actor_shows.append(i)
    else:
        print("{} not in any programme, perhaps try a different spelling...".format(cast_name))
       
    return actor_shows

def Cast_of(all_graph,show_name):
    G=all_graph[0]
    if show_name in G.nodes():
        # Returns all the actors which have been in a show
        cast_list=[]
        for i in nx.all_neighbors(G,show_name):
            print(i)
            cast_list.append(i)
    else:
        print("{} not in the listed programmes, perhaps try a different spelling...".format(show_name))   
    return cast_list

def Shows_in_common(all_graph,person_A, person_B):
    G=all_graph[0]
    common_shows=[]
    err_catch=0
    if person_A not in G.nodes():
        print("{} not in any programme, perhaps try a different spelling...".format(person_A))
        err_catch=1
    if person_B not in G.nodes():
        print("{} not in any programme, perhaps try a different spelling...".format(person_B))
        err_catch=1
        
    if err_catch==0:
        for i in nx.common_neighbors(G, person_A, person_B):
            print(i)
            common_shows.append(i)
    return common_shows
        
def Stars_of(all_graph,show_name):
    G=all_graph[0]
    other_shows=[] #List to hold the shows
    show_dict={} # Dictionary to hold the cast mapped to shows
    if show_name in G.nodes():
        for i in G.neighbors(show_name): #Loop through the cast of a show
            for j in G.neighbors(i): # For each cast member, loop through the shows they've been in 
                if j != show_name: #other than that originally specified
                    other_shows.append(j)
                    if i in show_dict:
                        show_dict[i].append(j)
                    else:
                        show_dict[i]=[j]
    else:
        print("{} not in the listed programmes, perhaps try a different spelling...".format(show_name))  
    other_shows=list(set(list(other_shows)))
    [print(x) for x in other_shows]
    return show_dict, other_shows

def cast_in_most_titles(top_N,all_graph):
    talent_nodes=all_graph[1]
    edges=all_graph[3]
    
    conn = sqlite3.connect('SQL_connection1.db') #Create a connection object
    query=conn.cursor()

    try:
        query.execute('''drop table edge_tab''')
    except:
        pass
    pd.DataFrame(edges,columns=['Node_1','Node_2','Weight']).to_sql('edge_tab',con=conn)

    try:
        query.execute('''drop table actor_tab''')
    except:
        pass
    pd.DataFrame(list(set(talent_nodes)),columns=['Actor_Node']).to_sql('actor_tab',con=conn)

    top_actors=pd.read_sql_query("""
        select Actor_node, count(*) as N_shows
        from
        (select 
        Actor_Node,
        Node_2 as show_node
        from 
            actor_tab a
        inner join
            edge_tab b
        on a.Actor_node=b.Node_1
        union all
        select 
        Actor_Node,
        Node_1 as show_node
        from 
            actor_tab a
        inner join
            edge_tab b
        on a.Actor_node=b.Node_2)
        group by 1 
        order by N_shows desc
            """, conn)
    return top_actors[0:top_N]

def shows_with_largest_cast(top_N,all_graph):
    show_nodes=all_graph[2]
    edges=all_graph[3]
    
    conn = sqlite3.connect('SQL_connection1.db') #Create a connection object
    query=conn.cursor()

    try:
        query.execute('''drop table edge_tab''')
    except:
        pass
    pd.DataFrame(edges,columns=['Node_1','Node_2','Weight']).to_sql('edge_tab',con=conn)

    try:
        query.execute('''drop table show_tab''')
    except:
        pass
    pd.DataFrame(list(set(show_nodes)),columns=['Show_node']).to_sql('show_tab',con=conn)

    top_shows=pd.read_sql_query("""
        select show_node, count(*) as N_cast
        from
        (select 
        show_node,
        Node_2 as Talent_node
        from 
            show_tab a
        inner join
            edge_tab b
        on a.show_node=b.Node_1
        union all
        select 
        show_node,
        Node_1 as Talent_node
        from 
            show_tab a
        inner join
            edge_tab b
        on a.show_node=b.Node_2)
        group by 1 
        order by N_cast desc
            """, conn)
    return top_shows[0:top_N]

def Is_there_a_path_between(all_graph,person_A,person_B):
    G=all_graph[0]
    if nx.has_path(G,person_A,person_B)==True:
        
        print("There is a path between {} and {}. You can get there via {} intermittent shows."\
              .format(person_A,person_B,nx.shortest_path_length(G,person_A,person_B)/2))
        
    else:
        print("There is not a path between {} and {} according to the data we have."\
              .format(person_A,person_B))

def paths_between(talent_graph,person_A,person_B,num_shows='shortest',layout='custom'):
    G=talent_graph[0]
    talent_nodes=talent_graph[1]
    show_nodes=talent_graph[2]
    
    all_paths=[]
    if nx.has_path(G,person_A,person_B)==True:
        if num_shows=='shortest':
            n='the fewest possible'
            all_paths=list(nx.all_shortest_paths(G,person_A,person_B))
        else:
            try:
                n=num_shows*2
                all_paths=list(nx.all_simple_paths(G,person_A,person_B,cutoff=n))
            except:
                print('Error: Enter a number or the word "shortest"')
    else:
        print("There is not a path between {} and {} according to the data we have, or the name(s) are misspelt."\
              .format(person_A,person_B))
    
    print("There are {} paths found between {} and {}".format(len(all_paths),person_A,person_B))
    if len(all_paths)>0:# There may be a path but it may be too long for the query
        # Create a subgraph of this
        subgraph_nodelist = list(set(list(itertools.chain.from_iterable(all_paths))))
        subgraph_G=G.subgraph(subgraph_nodelist)
        subgraph_show_nodes=G.subgraph([i for i in subgraph_nodelist if i in show_nodes])
        subgraph_talent_nodes=G.subgraph([i for i in subgraph_nodelist if i in talent_nodes])

        if layout=='custom':
            print_diamond_layout(all_paths,subgraph_G,subgraph_talent_nodes,subgraph_show_nodes\
                                 ,r"/Users/stepwate/Python Codes/Talent Graphs/Graph Outputs/{} to {} in {} steps.png".format(person_A, person_B,n))
        else:
            print_bipartite_subgraph(subgraph_G,subgraph_talent_nodes,subgraph_show_nodes\
                                 ,r"/Users/stepwate/Python Codes/Talent Graphs/Graph Outputs/{} to {} in {} steps.png".format(person_A, person_B,n),layout='spring')
    else:
        print("And so no Connections graph can be created")
        

    return all_paths

def print_bipartite_subgraph(G,talent_nodes,show_nodes,filename_to_export,layout='spring'):
    axsize = plt.subplots(figsize=(15,15))[1]# Set graph size for picture
    axsize.set_facecolor(bb_palette['Light Cloud']) # Set graph background colour
    plt.axis('off')

    if layout=='spring':
        positioning=nx.spring_layout(G)
    elif layout=='random':
        positioning=nx.random_layout(G)
    elif layout=='planar':
        positioning=nx.planar_layout(G)
    elif layout=='kamada':
        positioning=nx.kamada_kawai_layout(G)
    elif layout=='spectral':
        positioning=nx.spectral_layout(G)
    else:
        positioning=nx.random_layout(G)


    nx.draw_networkx_labels(G,pos=positioning,label_pos=-1,font_size=12,\
                            font_color=bb_palette['Dark Storm'],font_family='monserrat')
    nx.draw_networkx_nodes(G,pos=positioning,nodelist=show_nodes,node_color=bb_palette['Dorset Blue'],ax=axsize,node_shape="s")
    nx.draw_networkx_nodes(G,pos=positioning,nodelist=talent_nodes,node_color=bb_palette['Sunset Red'],ax=axsize,node_shape="*")
    nx.draw_networkx_edges(G,pos=positioning,edge_color=bb_palette['Union Blue'])
    
    plt.savefig(filename_to_export)
    
def print_diamond_layout(list_of_paths,G,talent_nodes,show_nodes,filename_to_export):
    # Set starting variables to empty
    max_path_length=0
    nodes_dict_pos={}
    
    # Loop each path
    for n,i in enumerate(list_of_paths):
        this_list_length=len(i) # Length of path

        if this_list_length>max_path_length:
            max_path_length=this_list_length # If path longer than previously seen, update longest path value

        # Loop each node within the path
        for m,j in enumerate(i):
            if j in nodes_dict_pos.keys():
                nodes_dict_pos[j]['num_lists']=nodes_dict_pos[j]['num_lists']+1#Increment the number of paths a node appears in
                nodes_dict_pos[j]['sum_list_pos']=nodes_dict_pos[j]['sum_list_pos']+m #Sum of list positions, e.g. starting node will be 0
                nodes_dict_pos[j]['sum_path_lengths']=nodes_dict_pos[j]['sum_path_lengths']+1        
            else:
                nodes_dict_pos[j]={'num_lists':1,'sum_list_pos':m,'sum_path_lengths':this_list_length}

    tot_num_paths=n+1 #Once iteration has finished, 
    print("There are {}".format(tot_num_paths))
    # Calculate average positions etc. X-co-ordinate will be the average position in a path so e.g. starting nodes are on the left and terminal nodes on the right
    nodes_dict_pos2=[]
    for key in nodes_dict_pos:
        nodes_dict_pos2.append({'node':key,\
                                'avg_pos_in_list':nodes_dict_pos[key]['sum_list_pos']/nodes_dict_pos[key]['num_lists'],\
                                'x_co':(nodes_dict_pos[key]['sum_list_pos']/nodes_dict_pos[key]['num_lists'])/max_path_length,\
                               'avg_length_of_lists':nodes_dict_pos[key]['sum_path_lengths']/nodes_dict_pos[key]['num_lists'],\
                                'num_paths':nodes_dict_pos[key]['num_lists'],\
                                'pc_paths':(nodes_dict_pos[key]['num_lists'])/tot_num_paths})

    # Load into a dataframe to make Y coordinate easier to code
    df=pd.DataFrame(nodes_dict_pos2)

    conn = sqlite3.connect('SQL_connection1.db') #Create a connection object
    query=conn.cursor()

    try:
        query.execute('''drop table node_positions''')
    except:
        pass
    df.to_sql('node_positions',con=conn)
    query.fetchall()
    query.close()
    # Specify logic for y- co-ordinate
    poslist=pd.read_sql_query("""select node,x_co,
    cast(row_number() over (partition by round(avg_pos_in_list) order by num_paths,avg_length_of_lists desc) as real)/
    (1+count(*) over (partition by round(avg_pos_in_list))) as y_co from node_positions a 
    order by round(avg_pos_in_list),avg_length_of_lists desc""",conn).to_dict(orient='rows')

    # Turn it into a dictionary holding relative positions
    positioning={}
    labelpos={}
    label_offset=0
    for i in poslist:
        positioning[i['node']]=np.asarray((i['x_co'],i['y_co']))
        labelpos[i['node']]=np.asarray((i['x_co']+label_offset,i['y_co']))
        
    axsize = plt.subplots(figsize=(15,15))[1]# Set graph size for picture
    axsize.set_facecolor(bb_palette['Light Cloud']) # Set graph background colour
    plt.axis('off')


    nx.draw_networkx_labels(G,pos=labelpos,label_pos=-1,font_size=12,font_color=bb_palette['Dark Storm'], font_family='monserrat')
    nx.draw_networkx_nodes(G,pos=positioning,nodelist=show_nodes,node_color=bb_palette['Dorset Blue'],ax=axsize,node_shape="s")
    nx.draw_networkx_nodes(G,pos=positioning,nodelist=talent_nodes,node_color=bb_palette['Sunset Red'],ax=axsize,node_shape="*")
    nx.draw_networkx_edges(G,pos=positioning,edge_color=bb_palette['Union Blue'])
    
    plt.savefig(filename_to_export)

def filter_graph(original_graph_set, pc_shows):
    
    new_graph=original_graph_set[0].copy()
    
    edges=original_graph_set[3]
    edges_to_remove=[]
    for x in edges:
        if x[2]<pc_shows:
            edges_to_remove.append((x[0],x[1]))
    
    # Remove weak edges
    new_graph.remove_edges_from(edges_to_remove)
    
    # And remove the nodes which are now no-longer connected since the edges have been removed
    new_graph.remove_nodes_from(list(nx.isolates(new_graph)))
    
    print("Graph originally had {} nodes and {} edges. Now Graph has {} nodes and {} edges by removing edges with a weight <{}".format\
         (original_graph_set[0].number_of_nodes(),original_graph_set[0].number_of_edges(),new_graph.number_of_nodes()\
         ,new_graph.number_of_edges(),pc_shows))
    
    
    new_edges=new_graph.edges()
    new_talent_nodes=[i for i in original_graph_set[1] if i in new_graph.nodes()]
    new_show_nodes=[i for i in original_graph_set[2] if i in new_graph.nodes()]
    
    return new_graph,new_talent_nodes, new_show_nodes, new_edges
