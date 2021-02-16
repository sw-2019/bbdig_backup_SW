create or replace view `itv-bde-analytics-dev.britbox_sandbox.ssna_1` as 
  (select *
  from `itv-bde-svod-dev.svod_entitlements.entitlements` 
  ) 
; 

create or replace view `itv-bde-analytics-dev.britbox_sandbox.ssna_2` as 
  (
  select a.*
  from `itv-bde-svod-dev.svod_entitlements.entitlements` as a 
  inner join 
    (select distinct user_id
    from `itv-bde-analytics-dev.britbox_sandbox.ssna_1` 
    where event_type like '%refund%'
    )as b 
  on a.user_id = b.user_id
  ) 
; 

create or replace view `itv-bde-analytics-dev.britbox_sandbox.ssna_3` as 
  (
  select a.*
  from `itv-bde-analytics-dev.britbox_sandbox.ssna_1` as a 
  inner join 
    (select distinct user_id
    from `itv-bde-analytics-dev.britbox_sandbox.ssna_2` 
    where event_type like '%refund%'
    )as b 
  on a.user_id = b.user_id
  ) 
; 

create or replace view `itv-bde-analytics-dev.britbox_sandbox.ssna_4` as 
  (
  select a.*
  from `itv-bde-analytics-dev.britbox_sandbox.ssna_3` as a 
  where event_type = 'new_entitlement'
  ) 
; 


