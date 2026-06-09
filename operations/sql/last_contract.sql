-- Latest contract header for a dealer account (:account_id).
SELECT
  cd.id,
  cd.bill_to_cdh_account_id,
  cd.bill_to_cdh_address_id,
  cd.bill_to_cdh_contact_id,
  cd.ship_to_cdh_account_id,
  cd.ship_to_cdh_address_id,
  cd.ship_to_cdh_contact_id,
  cd.currency_id,
  cd.term_uom,
  cd.term_quantity,
  cd.auto_renew,
  cd.status,
  cd.created_date
FROM contract.contract_detail cd
WHERE cd.bill_to_cdh_account_id = :account_id
  AND cd.is_deleted = false
ORDER BY cd.created_date DESC
LIMIT 1
