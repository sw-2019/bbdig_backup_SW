-- make full view paths
create or replace view `itv-bde-analytics-prd.britbox_analytics.network_analysis_views` as 
  (
  with 

  views as 
    (
    select 
      table_catalog
      , table_schema
      , table_name
      , trim(view_created) as destination_object
      , created_from2 as created_from
      , trim(case 
          when array_length(split(created_from2,".")) = 3 then created_from2
          when array_length(split(created_from2,".")) = 2 then concat('`',table_catalog,'.',trim(created_from2,'`'),'`') 
          else 'error'
      end) as created_from_full
      , view_definition as definition
      , 'view' as type
    from `itv-bde-analytics-prd.britbox_analytics.Scripts_all_views2` as a 
    cross join unnest(a.created_from) as created_from2
    )

  select *
  from views
  where 
      created_from_full <> 'error' 
      --and table_name like 'ssna_%'
  ) 
;

