with chains(chain_name, parent_chain, chain_owner) as (
    select :chain as chain_name, null as parent_chain, :owner as chain_owner from dual
    union all
    select s.program_name as chain_name, c.chain_name as parent_chain, program_owner as chain_owner
    from dba_scheduler_chain_steps s
    inner join chains c on (s.step_type = 'subchain' and s.chain_name = c.chain_name and s.owner = c.chain_owner)
 )
select ch.chain_owner, ch.chain_name as chain, s.step_name, r.condition, s.step_type, t.comments,
    regexp_instr(t.program_action, '^\w+(\.\w+)+$') as is_pkg,
    case when s.step_type = 'SUBCHAIN' then s.program_owner
        when regexp_like(t.program_action, '^\w+\.\w+$') then t.owner
        when regexp_like(t.program_action, '^\w+\.\w+\.\w+$') then upper(regexp_substr(t.program_action, '^\w+'))
    end as owner,
    case when s.step_type = 'SUBCHAIN' then s.program_name
        when regexp_like(t.program_action, '^\w+\.\w+$') then upper(regexp_substr(t.program_action, '^\w+'))
        when regexp_like(t.program_action, '^\w+\.\w+\.\w+$') then
                upper(trim(both '.' from regexp_substr(t.program_action, '\.\w+\.')))
    end as package,
    case when regexp_like(t.program_action, '^\w+(\.\w+)+$') then lower(regexp_substr(t.program_action, '\w+$')) else t.program_action end as procedure,
    decode(s.pause, 'TRUE','PAUSE') as pause, decode(s.pause_before, 'TRUE', 'PAUSE_BEFORE') as pause_before, decode(s.skip, 'TRUE', 'SKIP') as skip
from chains ch
inner join dba_scheduler_chain_steps s on (ch.chain_name = s.chain_name and s.owner = ch.chain_owner)
left outer join dba_scheduler_programs t on (t.program_name = s.program_name and s.program_owner = t.owner)
left outer join dba_scheduler_chain_rules r on (ch.chain_name = r.chain_name and r.owner = ch.chain_owner and r.action = 'START "' || s.step_name || '"')
order by ch.chain_owner, ch.chain_name, s.step_name