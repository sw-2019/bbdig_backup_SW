create or replace view `itv-bde-analytics-prd.britbox_analytics.Scripts_all_tables` as 
  (

  with 

  creates as 
    (
    select 
      project_id
      , user_email
      , end_time
      , query
      , destination_table
      , concat('`',destination_table.project_id,'.',destination_table.dataset_id,'.',destination_table.table_id,'`') as table_created
      , regexp_extract_all(query,'(`.*`)') as created_from
      , 'create table' as type
    from `itv-bde-analytics-dev.britbox_analytics.scripts_all_jobs`
    where 
      lower(query) like '%create%table%'
    ) 

  , schedules_no_create as 
    (
    select 
      project_id
      , user_email
      , end_time
      , query
      , destination_table
      , concat('`',destination_table.project_id,'.',destination_table.dataset_id,'.',destination_table.table_id,'`') as table_created
      , regexp_extract_all(query,'(`.*`)') as created_from
      , 'schedule no create' as type
    from `itv-bde-analytics-dev.britbox_analytics.scripts_all_jobs`
    where 
      job_id like 'scheduled_query%'
      and lower(query) not like '%create%table%'
    ) 

  , theunion as 
    (
    select 
      *
      , row_number() over (partition by table_created order by end_time desc) as last_run -- counter with 1 being the most recent run
    from  
      (
      select * from creates 
      UNION ALL 
      select * from schedules_no_create
      )
    ) 

  select *
  from theunion 
  where last_run = 1 
  ) 
; 


/* This is added stuff for testing purposes */