WITH chains(chain_name, parent_chain, chain_owner) AS (
    SELECT :chain AS chain_name, NULL AS parent_chain, :owner as chain_owner FROM dual
    UNION ALL
    SELECT s.PROGRAM_NAME AS chain_name, c.chain_name AS parent_chain, program_owner as chain_owner
    FROM dba_scheduler_chain_steps s
    INNER JOIN chains c ON (s.step_type  = 'SUBCHAIN' AND s.chain_name = c.chain_name and s.owner = c.chain_owner)
)
select owner, name as package_name, p_name as procedure_name, line, text
from (
    select owner, name, max(p_name) over (partition by owner, name, p order by line) as p_name, line, text
    from (
        select sum(p) over (partition by owner, name order by line) as p, p_name, owner, name, line, text
        from (
            select case when regexp_like(text, '^[[:blank:]|	]*(PROCEDURE|FUNCTION)[[:blank:]|	]+\w+', 'i') then 1 end as p,
            lower(regexp_replace(regexp_substr(text, '^[[:blank:]|	]*(PROCEDURE|FUNCTION)[[:blank:]|	]+\w+',1,1,'i'), '^[[:blank:]|	]*(PROCEDURE|FUNCTION)[[:blank:]|	]*','', 1,1,'i')) as p_name,
            owner, name, line, text
            from (
                select distinct
                    case when regexp_like(t.program_action, '^\w+\.\w+$') then t.owner
                        when regexp_like(t.program_action, '^\w+\.\w+\.\w+$') then upper(regexp_substr(t.program_action, '^\w+'))
                    end as schema_name,
                    case when regexp_like(t.program_action, '^\w+\.\w+$') then upper(regexp_substr(t.program_action, '^\w+'))
                        when regexp_like(t.program_action, '^\w+\.\w+\.\w+$') then upper(trim(both '.' from regexp_substr(t.program_action, '\.\w+\.')))
                    end as package_name
                from chains ch
                inner join dba_scheduler_chain_steps s on (ch.chain_name = s.chain_name and s.owner = ch.chain_owner)
                inner join dba_scheduler_programs t on (t.program_name  = s.program_name and s.program_owner = t.owner)
                where regexp_like(t.program_action, '^\w+(\.\w+)+$')
            ) p
            inner join all_source s on (s.owner = p.schema_name and s.name = p.package_name)
            where type = 'PACKAGE BODY'
        ) a
    ) b
) c
where p_name is not null
order by owner, name, p_name, line