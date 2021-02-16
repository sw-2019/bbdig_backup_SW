-- make full view paths
create or replace view `itv-bde-analytics-prd.britbox_analytics.network_analysis_tables` as 
  (
  with 

  tables as 
    (
    select 
      destination_table.project_id as table_catalog
      , destination_table.dataset_id as table_schema
      , destination_table.table_id as table_name
      , trim(table_created) as destination_object
      , created_from2 as created_from
      , trim(case 
          when array_length(split(created_from2,".")) = 3 then created_from2
          when array_length(split(created_from2,".")) = 2 then concat('`',project_id,'.',trim(created_from2,'`'),'`') 
          else 'error'
      end) as created_from_full
      , query as definition
      , 'table' as type
    from `itv-bde-analytics-prd.britbox_analytics.Scripts_all_tables` as a 
    cross join unnest(a.created_from) as created_from2
    )

  select *
  from tables
  where 
      created_from_full <> 'error' 
     -- and table_name like 'ssna_%'
      and destination_object <> created_from_full
  ) 
;

