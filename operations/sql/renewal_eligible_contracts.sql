-- Use with support_bot_sql_read. :account_id is bound to the dealer account ID.
-- For exact renewal rules, prefer renewal_eligible_contract_ids_tool (uses C# validation).
SELECT
  cd.id,
  cd.contract_number_search,
  cd.status,
  cd.renewal_date,
  cd.ship_to_cdh_account_id AS customer_id
FROM contract.contract_detail cd
WHERE cd.bill_to_cdh_account_id = :account_id
  AND cd.is_deleted = false
  AND cd.status IN ('ACTIVATED', 'EXPIRED')
  AND (cd.renewal_status IS NULL OR cd.renewal_status = 'RENEWAL_ERROR')
ORDER BY cd.renewal_date NULLS LAST
LIMIT 50
