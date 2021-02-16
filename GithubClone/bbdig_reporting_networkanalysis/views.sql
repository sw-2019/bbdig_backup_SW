create or replace view `itv-bde-analytics-prd.britbox_analytics.Scripts_all_views2` as 
  (

  select 
    table_catalog,
    table_schema,
    table_name,
    concat('`',table_catalog,'.',table_schema,'.',table_name,'`') as view_created,
    regexp_extract_all(view_definition,'(`.*`)') as created_from,
    view_definition
  from `itv-bde-analytics-dev.britbox_sandbox.INFORMATION_SCHEMA.VIEWS`

  union all 

  select 
    table_catalog,
    table_schema,
    table_name,
    concat('`',table_catalog,'.',table_schema,'.',table_name,'`') as view_created,
    regexp_extract_all(view_definition,'(`.*`)') as created_from,
    view_definition
  from `itv-bde-analytics-dev.britbox_analytics.INFORMATION_SCHEMA.VIEWS`

  union all

  select 
    table_catalog,
    table_schema,
    table_name,
    concat('`',table_catalog,'.',table_schema,'.',table_name,'`') as view_created,
    regexp_extract_all(view_definition,'(`.*`)') as created_from,
    view_definition
  from `itv-bde-analytics-prd.britbox_sandbox.INFORMATION_SCHEMA.VIEWS`

  union all 

  select 
    table_catalog,
    table_schema,
    table_name,
    concat('`',table_catalog,'.',table_schema,'.',table_name,'`') as view_created,
    regexp_extract_all(view_definition,'(`.*`)') as created_from,
    view_definition
  from `itv-bde-analytics-prd.britbox_analytics.INFORMATION_SCHEMA.VIEWS`

  union all 

  select 
    table_catalog,
    table_schema,
    table_name,
    concat('`',table_catalog,'.',table_schema,'.',table_name,'`') as view_created,
    regexp_extract_all(view_definition,'(`.*`)') as created_from,
    view_definition
  from `itv-bde-svod-prd.reporting.INFORMATION_SCHEMA.VIEWS`
  ) 
;